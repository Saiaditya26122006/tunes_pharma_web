from flask import Flask, render_template, request, session, redirect, jsonify, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import tempfile
import uuid as uuid_lib

try:
    from supabase_client import supabase as sb
except Exception:
    sb = None

# ── Email helper (Gmail SMTP — no extra package needed) ──────
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email_notification(doctor_email, doctor_name, paper_title, paper_description, paper_url, therapy_area):
    """Send a paper notification email to a single doctor via Gmail SMTP."""
    gmail_user = os.getenv('GMAIL_USER', '')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail_user or not gmail_pass or not doctor_email:
        return False
    try:
        therapy_label = {
            'diabetes': 'Diabetology', 'neuropathy': 'Neuropathy',
            'gastro': 'Gastroenterology', 'general': 'General Medicine'
        }.get(therapy_area, 'General')

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New Clinical Resource: {paper_title} | Tunes Pharma"
        msg['From']    = f"Tunes Pharma <{gmail_user}>"
        msg['To']      = doctor_email

        html = f"""
        <div style="font-family:'Poppins',Arial,sans-serif;max-width:580px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e8ecf0">
          <div style="background:linear-gradient(135deg,#0a1628,#1e3a52);padding:32px 36px;text-align:center">
            <p style="color:rgba(255,255,255,.5);font-size:12px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 8px">Tunes Pharma — Doctor Portal</p>
            <h1 style="color:#fff;font-size:22px;margin:0;font-weight:700">New Resource Published</h1>
          </div>
          <div style="padding:36px">
            <p style="color:#64748b;font-size:14px;margin:0 0 24px">Dear Dr. {doctor_name},</p>
            <div style="background:#f8fafc;border-radius:12px;padding:24px;border-left:4px solid #1e6ff1;margin-bottom:24px">
              <span style="display:inline-block;background:rgba(30,111,241,.1);color:#1e6ff1;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 10px;border-radius:20px;margin-bottom:12px">{therapy_label}</span>
              <h2 style="color:#0f1e2d;font-size:18px;margin:0 0 10px;line-height:1.4">{paper_title}</h2>
              <p style="color:#64748b;font-size:14px;line-height:1.7;margin:0">{paper_description or 'A new clinical resource has been added to your research library.'}</p>
            </div>
            <div style="text-align:center;margin-bottom:28px">
              <a href="{paper_url}" style="display:inline-block;background:#1e6ff1;color:#fff;padding:13px 32px;border-radius:50px;font-size:14px;font-weight:600;text-decoration:none">View Resource →</a>
            </div>
            <p style="color:#94a3b8;font-size:12px;text-align:center;margin:0">
              Log in anytime at <a href="https://tunespharma.in/doctor-portal" style="color:#1e6ff1">tunespharma.in/doctor-portal</a><br>
              to access your full research library and AI assistant.
            </p>
          </div>
          <div style="background:#f8fafc;padding:16px 36px;border-top:1px solid #e8ecf0;text-align:center">
            <p style="color:#94a3b8;font-size:11px;margin:0">Tunes Pharma · A Division of Brinda Medicals · Guntur, Andhra Pradesh</p>
          </div>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, doctor_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email] Failed to send to {doctor_email}: {e}")
        return False

app = Flask(__name__)
# Use /tmp for uploads — works both locally and on Vercel serverless
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tunes-therapeutics-secret-2024')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Language translations
translations = {
    'en': {
        'home': 'Home',
        'about': 'About',
        'products': 'Products',
        'services': 'Services',
        'research': 'Research',
        'contact': 'Contact',
        'gallery': 'Gallery',
        'pharmaintel_ai': 'Pharmaintel AI',
        'welcome': 'Welcome to Tunes Therapeutics',
        'tagline': 'Retuning Health, Redefining Lives'
    },
    'hi': {
        'home': 'होम',
        'about': 'हमारे बारे में',
        'products': 'उत्पाद',
        'services': 'सेवाएँ',
        'research': 'अनुसंधान',
        'contact': 'संपर्क करें',
        'gallery': 'गैलरी',
        'pharmaintel_ai': 'फार्माइंटेल AI',
        'welcome': 'ट्यून्स थेराप्यूटिक्स में आपका स्वागत है',
        'tagline': 'स्वास्थ्य को पुनः ट्यून करना, जीवन को पुनः परिभाषित करना'
    }
}

# Initialize OpenAI client (optional — only if API key is set)
client = None
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    try:
        from openai import OpenAI
        import markdown, PyPDF2
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}")

products_data = {
    "ecoglim-mv1": {
        "name": "Ecoglim MV 1mg/500mg/0.2mg Tablet SR",
        "description": "Ecoglim MV 1mg/500mg/0.2mg Tablet SR belongs to a category of medicines known as anti-diabetic drugs. It is a combination of medicines used to treat type 2 diabetes mellitus in adults. It helps control blood sugar levels in people with diabetes. Take it with or immediately before meals, regularly at the same time each day. Keep taking this medicine even if you feel well or your blood sugar levels are controlled — stopping without consulting your doctor may put you at risk of kidney damage, blindness, nerve problems, and loss of limbs.",
        "image": "ecoglim-mv1.jpg",
        "features": "Triple-action antidiabetic — controls fasting and post-prandial blood glucose through 3 distinct mechanisms",
        "composition": "Glimepiride 1mg + Metformin 500mg + Voglibose 0.2mg",
        "category": "Diabetes",
        "indication": "Treatment of Type 2 Diabetes Mellitus in adults — particularly effective for controlling post-meal blood glucose spikes when single or dual therapy is not effective.",
        "benefits": "Ecoglim MV 1mg/500mg/0.2mg Tablet SR helps control high blood glucose levels after meals and supports better overall diabetes management. It lowers the risk of serious complications of diabetes, such as kidney damage, vision problems, nerve issues, and limb loss. It also helps reduce the risk of death from cardiovascular disease in people with type 2 diabetes who already have heart disease. Regular use, along with a healthy diet and exercise, supports long-term health and helps maintain a more stable and active life.",
        "how_it_works": "Ecoglim MV is a combination of three antidiabetic medicines: Glimepiride, Metformin, and Voglibose. Glimepiride is a sulfonylurea that increases the amount of insulin released by the pancreas to lower blood glucose. Metformin is a biguanide that lowers glucose production in the liver, delays glucose absorption from the intestines, and increases the body's sensitivity to insulin. Voglibose is an alpha-glucosidase inhibitor that prevents the breakdown of complex sugars into simple sugars (glucose), preventing blood glucose levels from rising too high after meals.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Ecoglim MV 1mg/500mg/0.2mg Tablet SR is to be taken on an empty stomach (with or immediately before meals). If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Constipation, Nausea, Hypoglycemia (low blood glucose level), Abdominal pain, Loss of appetite. Also reported: Vomiting, Diarrhoea, Taste changes, Headache, Edema (swelling), Blurred vision, Upper respiratory tract infection. Recognise signs of low blood sugar: sweating, dizziness, headache, and shaking. Always carry a fast-acting glucose source. Most side effects do not require medical attention and disappear as your body adjusts to the medicine.",
        "safety_advice": "Alcohol: UNSAFE — It is unsafe to consume alcohol with this medicine. It may lower blood sugar levels and increase the chances of lactic acidosis. Pregnancy: CONSULT YOUR DOCTOR — Safety during pregnancy has not been established. Breastfeeding: CONSULT YOUR DOCTOR — May pass into breastmilk and harm the baby. Driving: CAUTION — May affect driving ability if blood sugar becomes too low or too high; monitor your blood glucose. Kidney: UNSAFE — Unsafe in patients with kidney disease and should be avoided; not recommended in severe kidney disease. Liver: CAUTION — Use with caution in liver disease; generally started with low dose in mild-to-moderate disease; not recommended in severe liver disease.",
        "contraindications": "Do not take if you have type 1 diabetes mellitus, diabetic ketoacidosis, severe kidney or liver disease, or inflammatory bowel disease. Not suitable if you have a history of heart disease (consult doctor). Avoid in known allergy to any component. Avoid with alcohol.",
        "drug_interactions": "Inform your doctor about all medicines you are taking. Ecoglim MV can cause hypoglycemia when used with other antidiabetic medicines or alcohol, or if you delay/miss a meal. Your doctor may check your liver function regularly — inform if you develop abdominal pain, loss of appetite, or jaundice.",
        "quick_tips": "Can cause hypoglycemia (low blood sugar) when used with other antidiabetic medicines or alcohol — always carry a sugar source for immediate relief. Your doctor may check liver function regularly; inform if you develop abdominal pain, loss of appetite, or yellowing of eyes/skin. Individuals with severe renal or hepatic impairment should not take this medicine. Works best when used along with proper diet and exercise. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹7.78/Tablet SR",
        "therapeutic_class": "ANTI DIABETIC",
        "buy_1mg": "https://www.1mg.com/drugs/ecoglim-mv-1mg-500mg-0.2mg-tablet-sr-725563"
    },
    "ecoglim-mv2": {
        "name": "Ecoglim MV 2mg/500mg/0.2mg Tablet SR",
        "description": "Ecoglim MV 2mg/500mg/0.2mg Tablet SR belongs to a category of medicines known as anti-diabetic drugs. It is a combination of medicines used to treat type 2 diabetes mellitus in adults. It helps control blood sugar levels in people with diabetes. Take it with or immediately before meals, regularly at the same time each day. Keep taking this medicine even if you feel well or your blood sugar levels are controlled — stopping without consulting your doctor may put you at risk of kidney damage, blindness, nerve problems, and loss of limbs.",
        "image": "ecoglim-mv2.jpg",
        "features": "Triple-action antidiabetic — higher Glimepiride dose (2mg) for patients requiring stronger glycemic control",
        "composition": "Glimepiride 2mg + Metformin 500mg + Voglibose 0.2mg",
        "category": "Diabetes",
        "indication": "Treatment of Type 2 Diabetes Mellitus in adults requiring stronger glycemic control — particularly effective for post-meal blood glucose management when lower doses are insufficient.",
        "benefits": "Ecoglim MV 2mg/500mg/0.2mg Tablet SR helps control high blood glucose levels after meals and supports better overall diabetes management with a higher Glimepiride dose (2mg). It lowers the risk of serious complications of diabetes, such as kidney damage, vision problems, nerve issues, and limb loss. It also helps reduce the risk of cardiovascular mortality in patients with type 2 diabetes who already have heart disease. Regular use, combined with a healthy diet and exercise, supports long-term health and a more stable, active life.",
        "how_it_works": "Ecoglim MV is a combination of three antidiabetic medicines: Glimepiride, Metformin, and Voglibose. Glimepiride (2mg) is a sulfonylurea that increases the amount of insulin released by the pancreas to lower blood glucose. Metformin is a biguanide that lowers glucose production in the liver, delays glucose absorption from the intestines, and increases the body's sensitivity to insulin. Voglibose is an alpha-glucosidase inhibitor that prevents the breakdown of complex sugars into simple sugars (glucose), preventing blood glucose levels from rising too high after meals.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Ecoglim MV 2mg/500mg/0.2mg Tablet SR is to be taken on an empty stomach (with or immediately before meals). If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Constipation, Nausea, Hypoglycemia (low blood glucose level), Abdominal pain, Loss of appetite. Also reported: Vomiting, Diarrhoea, Taste changes, Headache, Edema (swelling), Blurred vision, Upper respiratory tract infection. Recognise signs of low blood sugar: sweating, dizziness, headache, and shaking. Always carry a fast-acting glucose source. Most side effects do not require medical attention and disappear as your body adjusts.",
        "safety_advice": "Alcohol: UNSAFE — It is unsafe to consume alcohol with this medicine. It may lower blood sugar levels and increase the chances of lactic acidosis. Pregnancy: CONSULT YOUR DOCTOR — Safety during pregnancy has not been established. Breastfeeding: CONSULT YOUR DOCTOR — May pass into breastmilk and harm the baby. Driving: CAUTION — May affect driving ability if blood sugar becomes too low or too high; monitor your blood glucose. Kidney: UNSAFE — Unsafe in patients with kidney disease and should be avoided; not recommended in severe kidney disease. Liver: CAUTION — Use with caution in liver disease; generally started with low dose in mild-to-moderate disease; not recommended in severe liver disease.",
        "contraindications": "Do not take if you have type 1 diabetes mellitus, diabetic ketoacidosis, severe kidney or liver disease, or inflammatory bowel disease. Not suitable if you have a history of heart disease (consult doctor). Avoid in known allergy to any component. Avoid with alcohol.",
        "drug_interactions": "Inform your doctor about all medicines you are taking. This medicine can cause hypoglycemia when used with other antidiabetic medicines or alcohol, or if you delay/miss a meal. Your doctor may check your liver function regularly — inform if you develop abdominal pain, loss of appetite, or jaundice.",
        "quick_tips": "Can cause hypoglycemia (low blood sugar) when used with other antidiabetic medicines or alcohol — always carry a sugar source for immediate relief. Your doctor may check liver function regularly; inform if you develop abdominal pain, loss of appetite, or yellowing of eyes/skin. Individuals with severe renal or hepatic impairment should not take this medicine. Works best when used along with proper diet and exercise. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹8.50/Tablet SR",
        "therapeutic_class": "ANTI DIABETIC",
        "buy_1mg": "https://www.1mg.com/drugs/ecoglim-mv-2mg-500mg-0.2mg-tablet-sr-725565"
    },
    "ecoglim-mp1": {
        "name": "Ecoglim MP 1mg/500mg/15mg Tablet SR",
        "description": "Ecoglim MP 1mg/500mg/15mg Tablet SR is a medicine that helps control blood sugar levels. It is used together with diet and exercise to improve blood sugar control in adults with type 2 diabetes mellitus. It helps in the proper utilisation of insulin, thereby lowering blood sugar levels. Take it with food to avoid stomach upset. Overdose may lead to low blood sugar (hypoglycemia).",
        "image": "ecoglim-mp1.jpg",
        "features": "Triple-action antidiabetic — improves insulin utilisation through 3 distinct mechanisms for better glycemic control",
        "composition": "Glimepiride 1mg + Metformin 500mg + Pioglitazone 15mg",
        "category": "Diabetes",
        "indication": "Treatment of Type 2 Diabetes Mellitus in adults — used when single or dual therapy is not effective. Supports better use of insulin and reduces excess glucose levels in the body.",
        "benefits": "Ecoglim MP 1mg/500mg/15mg Tablet SR helps improve blood sugar control by supporting better use of insulin and reducing excess glucose levels in the body. It helps maintain more stable sugar levels throughout the day, lowers the risk of diabetes-related complications (kidney damage, vision problems, nerve issues, limb loss), and supports overall metabolic health when used along with a proper diet and lifestyle.",
        "how_it_works": "Ecoglim MP is a combination of three antidiabetic medicines: Glimepiride, Metformin, and Pioglitazone. Glimepiride is a sulfonylurea that increases the amount of insulin released by the pancreas to lower blood glucose. Metformin is a biguanide that lowers glucose production in the liver, reduces glucose absorption from the intestines, and increases the body's sensitivity to insulin. Pioglitazone is a thiazolidinedione that further increases insulin sensitivity by acting on PPAR-γ receptors in fat and muscle tissue. Together, they provide better blood sugar control when single or dual therapy is insufficient.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Ecoglim MP 1mg/500mg/15mg Tablet SR should be taken with or after food. If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Cardiac disturbances, Pain in extremity, Back pain, Chest pain, Headache, Sinus inflammation, Muscle pain, Sore throat. Also: Hypoglycemia (low blood sugar — symptoms include cold sweats, cool pale skin, tremor, anxiety, fast heart rate, dizziness, nausea). Most side effects do not require medical attention and disappear as your body adjusts. Consult your doctor if they persist.",
        "safety_advice": "Alcohol: UNSAFE — Unsafe to consume alcohol; may lower blood sugar and increase risk of lactic acidosis. Pregnancy: UNSAFE — Highly unsafe during pregnancy; can cause serious harm including birth defects and pregnancy loss. Do not use if pregnant or planning pregnancy. Breastfeeding: UNSAFE — Unsafe during breastfeeding; data suggests the drug may cause toxicity to the baby. Driving: UNSAFE — May decrease alertness, affect vision, or cause sleepiness and dizziness; do not drive if these symptoms occur. Kidney: CAUTION — Use with caution in kidney disease; not recommended in severe kidney disease; regular monitoring of kidney function is advisable. Liver: UNSAFE — Unsafe in patients with liver disease and should be avoided; not recommended in severe liver disease.",
        "contraindications": "Avoid in congestive heart failure, severe kidney disease, severe liver disease, swelling of the back of the eye. Do not use if pregnant or breastfeeding. Avoid alcohol. Not for type 1 diabetes or diabetic ketoacidosis. Avoid in known allergy to any component.",
        "drug_interactions": "Inform your doctor about all prescription and non-prescription medicines, vitamins, and herbal supplements you are taking. Long-term use may cause Vitamin B12 deficiency (Metformin interferes with B12 absorption). Inform your doctor about any kidney, liver, or heart problems before starting treatment.",
        "quick_tips": "Take it with food to lower the chance of an upset stomach. May cause hypoglycemia when used with other antidiabetic medicines, alcohol, or if you delay/miss a meal — always carry sugary food or fruit juice for immediate relief. Your doctor may check liver function regularly — inform if you develop abdominal pain, loss of appetite, or yellowing of eyes/skin. Works best along with proper diet and exercise. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹3.89/Tablet SR",
        "therapeutic_class": "ANTI DIABETIC",
        "buy_1mg": "https://www.1mg.com/drugs/ecoglim-mp-1mg-500mg-15mg-tablet-sr-725567"
    },
    "ecoglim-mp2": {
        "name": "Ecoglim MP 2mg/500mg/15mg Tablet SR",
        "description": "Ecoglim MP 2mg/500mg/15mg Tablet SR is a medicine that helps control blood sugar levels. It is used together with diet and exercise to improve blood sugar control in adults with type 2 diabetes mellitus. It contains a higher dose of Glimepiride (2mg) for patients requiring stronger glycemic control. It helps in the proper utilisation of insulin, thereby lowering blood sugar levels. Take it with food to avoid stomach upset. Overdose may lead to low blood sugar (hypoglycemia).",
        "image": "ecoglim-mp2.jpg",
        "features": "Triple-action antidiabetic with higher Glimepiride dose (2mg) — for patients needing stronger insulin stimulation and glycemic control",
        "composition": "Glimepiride 2mg + Metformin 500mg + Pioglitazone 15mg",
        "category": "Diabetes",
        "indication": "Treatment of Type 2 Diabetes Mellitus in adults requiring stronger glycemic control — used when the 1mg dose is insufficient or when more pronounced insulin resistance is present.",
        "benefits": "Ecoglim MP 2mg/500mg/15mg Tablet SR helps improve blood sugar control with a higher Glimepiride dose (2mg) for stronger insulin stimulation. It maintains more stable sugar levels throughout the day, lowers the risk of diabetes-related complications (kidney damage, vision problems, nerve issues, limb loss), and supports overall metabolic health when used along with a proper diet and lifestyle.",
        "how_it_works": "Ecoglim MP is a combination of three antidiabetic medicines: Glimepiride, Metformin, and Pioglitazone. Glimepiride (2mg) is a sulfonylurea that increases the amount of insulin released by the pancreas to lower blood glucose — at a stronger dose than the 1mg formulation. Metformin is a biguanide that lowers glucose production in the liver, reduces glucose absorption from the intestines, and increases the body's sensitivity to insulin. Pioglitazone is a thiazolidinedione that further increases insulin sensitivity by acting on PPAR-γ receptors in fat and muscle tissue. Together, they provide better blood sugar control when single or dual therapy is insufficient.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Ecoglim MP 2mg/500mg/15mg Tablet SR should be taken with or after food. If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Cardiac disturbances, Pain in extremity, Back pain, Chest pain, Headache, Sinus inflammation, Muscle pain, Sore throat. Also: Hypoglycemia (low blood sugar — symptoms include cold sweats, cool pale skin, tremor, anxiety, fast heart rate, dizziness, nausea). Most side effects do not require medical attention and disappear as your body adjusts. Consult your doctor if they persist.",
        "safety_advice": "Alcohol: UNSAFE — Unsafe to consume alcohol; may lower blood sugar and increase risk of lactic acidosis. Pregnancy: UNSAFE — Highly unsafe during pregnancy; can cause serious harm including birth defects and pregnancy loss. Do not use if pregnant or planning pregnancy. Breastfeeding: UNSAFE — Unsafe during breastfeeding; data suggests the drug may cause toxicity to the baby. Driving: UNSAFE — May decrease alertness, affect vision, or cause sleepiness and dizziness; do not drive if these symptoms occur. Kidney: CAUTION — Use with caution in kidney disease; not recommended in severe kidney disease; regular monitoring of kidney function is advisable. Liver: UNSAFE — Unsafe in patients with liver disease and should be avoided; not recommended in severe liver disease.",
        "contraindications": "Avoid in congestive heart failure, severe kidney disease, severe liver disease, swelling of the back of the eye. Do not use if pregnant or breastfeeding. Avoid alcohol. Not for type 1 diabetes or diabetic ketoacidosis. Avoid in known allergy to any component.",
        "drug_interactions": "Inform your doctor about all prescription and non-prescription medicines, vitamins, and herbal supplements you are taking. Long-term use may cause Vitamin B12 deficiency (Metformin interferes with B12 absorption). Inform your doctor about any kidney, liver, or heart problems before starting treatment.",
        "quick_tips": "Take it with food to lower the chance of an upset stomach. May cause hypoglycemia when used with other antidiabetic medicines, alcohol, or if you delay/miss a meal — always carry sugary food or fruit juice for immediate relief. Your doctor may check liver function regularly — inform if you develop abdominal pain, loss of appetite, or yellowing of eyes/skin. Works best along with proper diet and exercise. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹4.50/Tablet SR",
        "therapeutic_class": "ANTI DIABETIC",
        "buy_1mg": "https://www.1mg.com/drugs/ecoglim-mp-2mg-500mg-15mg-tablet-sr-725568"
    },
    "nactaid": {
        "name": "Nactaid 500mg/150mg Tablet",
        "description": "Nactaid 500mg/150mg Tablet is a combination medicine used in the treatment of chronic kidney disease. It protects the kidneys from damage and reduces the risk of kidney failure. It can be taken with or without food in a dose and duration as advised by the doctor. Keep taking this medicine for as long as your doctor recommends — stopping early may worsen your condition.",
        "image": "nactaid.jpg",
        "features": "Dual antioxidant combination — protects kidneys from free radical damage and slows progression of chronic kidney disease",
        "composition": "Taurine 500mg + Acetylcysteine 150mg",
        "category": "Nephrology",
        "indication": "Treatment of Chronic Kidney Disease (CKD). Also used to help prevent contrast-induced acute kidney injury (CI-AKI) in high-risk patients such as those with kidney problems, diabetes, high blood pressure, heart failure, older age, dehydration, or those taking kidney-harming medicines.",
        "benefits": "Chronic kidney disease (CKD) refers to the loss of normal kidney function over a long span of time. Nactaid 500mg/150mg Tablet has antioxidant properties that help in the elimination of toxic materials such as urea from the kidneys and improve kidney function. When combined with a low or very low protein diet, it helps slow down the progression of CKD and improves quality of life. Regular use as directed by the doctor provides maximum benefit.",
        "how_it_works": "Nactaid 500mg/150mg Tablet is a combination of two antioxidants: Taurine and Acetylcysteine. These antioxidants work by protecting the kidneys from damage by harmful chemicals (free radicals). Acetylcysteine is a precursor to glutathione — the body's primary cellular antioxidant — and helps neutralise oxidative stress in kidney tissue. Taurine supports cellular membrane stability, reduces inflammation, and provides additional antioxidant protection to renal cells.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Nactaid 500mg/150mg Tablet should be taken with or after food. If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Runny nose, Diarrhoea, Abdominal pain, Skin irritation, Throat irritation, Nausea, Vomiting, Rash, Fever. Most side effects do not require any medical attention and disappear as your body adjusts to the medicine. Contact your doctor if they persist or worsen.",
        "safety_advice": "Alcohol: CAUTION — Alcohol should be used with caution while taking this medicine. Pregnancy: CONSULT YOUR DOCTOR — Not recommended during pregnancy as there is positive evidence of fetal risk based on animal studies; may still be prescribed where benefits outweigh risks. Breastfeeding: CONSULT YOUR DOCTOR — May be unsafe; limited human data suggests the drug may pass into breastmilk and harm the baby; use only if expected benefit outweighs potential risk. Driving: UNSAFE — May decrease alertness, affect vision, or cause sleepiness and dizziness; do not drive if these symptoms occur. Kidney: SAFE IF PRESCRIBED — Safe to use in patients with kidney disease; no dose adjustment recommended. Liver: CONSULT YOUR DOCTOR — Limited data available on use in liver disease.",
        "contraindications": "Do not take if you are allergic to taurine, acetylcysteine, or any other ingredient in the medicine. Not recommended for people having a sudden, severe asthma attack — asthma patients should be closely monitored. Inform your doctor about any kidney or liver disease before starting treatment.",
        "drug_interactions": "Let your doctor know about all other medications you are taking, as some may affect or be affected by this medicine. Inform your doctor if you are pregnant, planning to conceive, or breastfeeding.",
        "quick_tips": "Take only as per the dose and duration prescribed by your doctor. The medicine has a characteristic smell — this is normal and does not indicate that the medicine has changed. Inform your doctor if you are pregnant, planning to conceive, or breastfeeding. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹8.64/Tablet",
        "therapeutic_class": "UROLOGY",
        "buy_1mg": "https://www.1mg.com/drugs/nactaid-500mg-150mg-tablet-725571"
    },
    "resgaba-nt": {
        "name": "Resgaba NT 75mg/10mg/1500mcg Tablet",
        "description": "Resgaba NT 75mg/10mg/1500mcg Tablet is a combination of three medicines used to treat neuropathic pain. It works by decreasing pain by controlling calcium channel activity of the nerve cells. It also increases the level of chemical messengers in the brain that help in regulating the mood and protect nerve fibers. Resgaba NT Tablet can be taken with or without food. However, it is advised to take it at the same time each day to maintain a consistent level of medicine in the body.",
        "image": "resgaba-nt.jpg",
        "features": "Triple-action neuropathic pain relief — targets pain signalling, mood pathways and nerve regeneration",
        "composition": "Pregabalin 75mg + Nortriptyline 10mg + Methylcobalamin 1500mcg",
        "category": "Neuropathy",
        "indication": "Treatment of Neuropathic Pain — including long-lasting (chronic) pain caused by nerve damage due to diabetes (diabetic peripheral neuropathy), shingles (post-herpetic neuralgia), or spinal cord injury.",
        "benefits": "Resgaba NT reduces pain and its associated symptoms such as mood changes, sleep problems, and tiredness. It works by interfering with pain signals that travel through the damaged nerves and the brain. It also contains nutritional supplements (Methylcobalamin) essential for improving nerve conduction. Taking Resgaba NT regularly will improve your physical and social functioning and overall quality of life. It takes a few weeks to work so it should be taken regularly even if it does not seem to be doing any good initially.",
        "how_it_works": "Pregabalin is an alpha 2 delta ligand which decreases pain by modulating calcium channel activity of the nerve cells. Nortriptyline is a tricyclic antidepressant which increases the levels of chemical messengers (serotonin and noradrenaline) that stop the movement of pain signals in the brain. Methylcobalamin is a form of vitamin B which helps in the production of myelin, a substance that protects nerve fibers and rejuvenates damaged nerve cells. Together, they relieve neuropathic pain (pain from damaged nerves).",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Resgaba NT Tablet may be taken with or without food. It is advised to take it at the same time each day. If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose. Do not stop taking this medicine suddenly without consulting your doctor — gradual tapering may be required.",
        "side_effects": "Constipation, Weight gain, Dizziness, Sleepiness, Tiredness, Blurred vision, Dryness in mouth, Uncoordinated body movements, Decreased appetite, Difficulty in urination, Orthostatic hypotension (sudden lowering of blood pressure on standing), Increased heart rate, Nausea, Vomiting, Diarrhea, Headache. Most side effects do not require medical attention and disappear as the body adjusts to the medicine. Consult your doctor if they persist.",
        "safety_advice": "Alcohol: UNSAFE — Do not drink alcohol while taking this medicine; may cause excessive drowsiness. Pregnancy: CONSULT YOUR DOCTOR — safety during pregnancy has not been established. Breastfeeding: CONSULT YOUR DOCTOR — may pass into breastmilk and harm the baby. Driving: UNSAFE — may affect alertness and ability to drive. Kidney disease: CAUTION — use with caution; dose adjustment may be needed. Liver disease: SAFE IF PRESCRIBED — dose adjustment may not be needed.",
        "contraindications": "Inform your doctor if you suffer from kidney or liver disease. Do not take with alcohol. Inform your doctor if you are pregnant, planning pregnancy, or breastfeeding. Immediately seek medical help if you experience hallucinations, fever, sweating, shivering, fast heart rate, muscle twitching, or loss of coordination.",
        "drug_interactions": "Inform your doctor about all other medicines you are taking as many of these may make this medicine less effective or change the way it works. Inform your doctor if you are taking any other pain-relieving medicines. Inform your doctor if you have a history of seizures.",
        "quick_tips": "Take it at the same time each day for consistent levels. Do not drive or operate machinery until you know how this medicine affects you. Maintain a balanced diet and exercise regularly to manage potential weight gain. Along with Resgaba NT, your doctor might advise physiotherapy to get relief from pain. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)",
        "mrp": "₹12.1/Tablet",
        "therapeutic_class": "NEURO CNS",
        "buy_1mg": "https://www.1mg.com/drugs/resgaba-nt-75mg-10mg-1500mcg-tablet-725572"
    },
    "resgaba-dlx": {
        "name": "RESGABA-DLX",
        "description": "RESGABA-DLX combines Pregabalin and Duloxetine for dual-action management of chronic neuropathic pain. Pregabalin modulates calcium channels in hyperexcited neurons while Duloxetine (SNRI) inhibits serotonin and noradrenaline reuptake to enhance descending pain control.",
        "image": "resgaba-dlx.jpg",
        "features": "Pregabalin 75mg + Duloxetine 30mg",
        "benefits": "Superior pain relief through central and peripheral sensitization blockade, mood improvement, and reduced anxiety — especially beneficial in patients with comorbid depression and chronic pain.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Ortho",
        "composition": "Pregabalin 75mg + Duloxetine 30mg",
        "indication": "Chronic neuropathic pain, diabetic peripheral neuropathy, generalized anxiety disorder, fibromyalgia",
        "how_to_use": "Take once or twice daily as directed. Do not crush, chew or open capsules. Do not stop abruptly — taper gradually.",
        "side_effects": "Nausea, dizziness, dry mouth, constipation, somnolence, hyperhidrosis. Monitor for suicidal ideation in initial weeks.",
        "storage": "Store below 30°C in a dry place away from moisture and direct sunlight.",
        "schedule": "H",
        "packing": "10×10 Capsules (Alu-Alu)"
    },
    "rabishir-dsr": {
        "name": "Rabishir D 30mg/20mg Capsule SR",
        "description": "Rabishir D 30mg/20mg Capsule SR is a combination medicine used to treat gastroesophageal reflux disease (acid reflux). It works by relieving symptoms of acidity such as heartburn, stomach pain, or irritation. It also neutralizes the acid and promotes easy passage of gas to reduce stomach discomfort. Take it on an empty stomach in the dose and duration advised by your doctor. Continue taking it for as long as prescribed — stopping early may cause symptoms to return or worsen.",
        "image": "rabishir-dsr.jpg",
        "features": "Dual-action GI relief — reduces stomach acid (Rabeprazole) and improves gastric motility (Domperidone SR)",
        "composition": "Domperidone 30mg + Rabeprazole 20mg",
        "category": "Gastrointestinal",
        "indication": "Treatment of Gastroesophageal Reflux Disease (GERD / Acid Reflux). Also used in gastric and duodenal ulcers and functional dyspepsia with nausea.",
        "benefits": "Gastroesophageal reflux disease (GERD) is a chronic condition where excess stomach acid flows back into the esophagus. Rabishir D reduces the amount of acid your stomach makes and relieves the pain associated with heartburn and acid reflux. Lifestyle changes that help: avoid trigger foods, eat smaller more frequent meals, lose weight if overweight, avoid eating within 3–4 hours of bedtime, and avoid spicy foods, coffee, tea, and chocolate. Taking cold milk and avoiding alcohol also enhances treatment effectiveness.",
        "how_it_works": "Rabishir D 30mg/20mg Capsule SR is a combination of two medicines: Domperidone and Rabeprazole. Domperidone is a prokinetic which works on the upper digestive tract to increase the movement of the stomach and intestines, allowing food to move more easily through the stomach — controlling nausea and preventing reflux. Rabeprazole is a proton pump inhibitor (PPI) which works by reducing the amount of acid produced in the stomach, providing relief from acid-related indigestion and heartburn.",
        "how_to_use": "Take this medicine in the dose and duration as advised by your doctor. Swallow it as a whole — do not chew, crush or break it. Rabishir D 30mg/20mg Capsule SR is to be taken on an empty stomach, preferably one hour before a meal (ideally in the morning). If you miss a dose, take it as soon as possible. However, if it is almost time for your next dose, skip the missed dose. Do not double the dose.",
        "side_effects": "Flatulence, Back pain, Cough, Headache, Diarrhoea, Dizziness, Inflammation of the nose, Abdominal pain, Vomiting, Insomnia (difficulty sleeping), Nausea, Constipation, Nasal congestion (stuffy nose), Fundic gland polyps. Dry mouth may also occur due to Domperidone — drink plenty of water if this happens. Most side effects are mild, temporary and disappear as your body adjusts.",
        "safety_advice": "Alcohol: CONSULT YOUR DOCTOR — It is not known whether it is safe to consume alcohol with this medicine; avoid alcohol as it can increase drowsiness. Pregnancy: UNSAFE — Highly unsafe during pregnancy; can cause serious harm to the unborn baby including birth defects and pregnancy loss; do not use if pregnant or planning pregnancy. Breastfeeding: UNSAFE — Unsafe during breastfeeding; data suggests the drug may cause toxicity to the baby. Driving: UNSAFE — May decrease alertness, affect vision, or cause sleepiness and dizziness; do not drive if these symptoms occur. Kidney: CAUTION — Use with caution in patients with severe kidney disease; dose adjustment may be needed. Liver: UNSAFE — Unsafe in patients with liver disease; not recommended in moderate and severe liver disease.",
        "contraindications": "Do not use if you have known hypersensitivity to rabeprazole, domperidone, or any inactive ingredients. Caution in patients with underlying kidney or liver disease. Do not use if pregnant or breastfeeding.",
        "drug_interactions": "Inform your healthcare provider about all other medicines you are taking, as some may interact with this medicine. Avoid alcohol. Inform your doctor if you have liver or kidney problems before starting treatment.",
        "quick_tips": "Take one hour before the meal, preferably in the morning. It is a well-tolerated medicine and provides relief for a long time. Inform your doctor if you experience watery diarrhoea, fever, or persistent stomach pain. Inform your doctor if you do not feel better after 14 days — you may have another condition that needs attention. Long-term use can cause weak bones and deficiency of minerals such as magnesium — take adequate dietary calcium and magnesium or supplements as prescribed. Habit Forming: No.",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "manufacturer": "Tunes Pharma, No. 8-274, Gowtham Nagar, Ferozguda, Balanagar, Hyderabad – 500 011.",
        "schedule": "H",
        "packing": "10×10 Capsules (Alu-Alu)",
        "mrp": "₹8.48/Capsule SR",
        "therapeutic_class": "GASTRO INTESTINAL",
        "buy_1mg": "https://www.1mg.com/drugs/rabishir-d-30mg-20mg-capsule-sr-725562"
    }
}

# Stockist/Dealer Data
stockists_data = [
    {
        "name": "Medicare Distributors",
        "city": "Mumbai",
        "state": "Maharashtra",
        "address": "123, Medical Street, Andheri East",
        "phone": "+91 9876543210",
        "email": "mumbai@medicare.com",
        "pincode": "400069"
    },
    {
        "name": "Health Care Suppliers",
        "city": "Delhi",
        "state": "Delhi",
        "address": "456, Pharma Road, Connaught Place",
        "phone": "+91 9876543211",
        "email": "delhi@healthcare.com",
        "pincode": "110001"
    },
    {
        "name": "Guntur Medical Distributors",
        "city": "Guntur",
        "state": "Andhra Pradesh",
        "address": "789, Hospital Road, Guntur",
        "phone": "+91 9876543212",
        "email": "guntur@medical.com",
        "pincode": "522001"
    },
    {
        "name": "Bangalore Pharma Hub",
        "city": "Bangalore",
        "state": "Karnataka",
        "address": "321, Industrial Area, Whitefield",
        "phone": "+91 9876543213",
        "email": "bangalore@pharma.com",
        "pincode": "560066"
    },
    {
        "name": "Chennai Medical Supplies",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "address": "654, Medical College Road, T Nagar",
        "phone": "+91 9876543214",
        "email": "chennai@medical.com",
        "pincode": "600017"
    }
]

# Regulatory Compliance Data
regulatory_data = {
    "certifications": [
        {"name": "GMP Certification", "issued_by": "DCGI", "valid_until": "2025-12-31"},
        {"name": "ISO 9001:2015", "issued_by": "Bureau Veritas", "valid_until": "2026-06-30"},
        {"name": "WHO-GMP", "issued_by": "WHO", "valid_until": "2025-12-31"},
        {"name": "Schedule M License", "issued_by": "DCGI", "valid_until": "2025-12-31"}
    ],
    "approvals": [
        {"product": "Ecoglim MV1", "approval_number": "DCGI/2023/12345", "date": "2023-01-15"},
        {"product": "NACTAID", "approval_number": "DCGI/2023/12346", "date": "2023-02-20"},
        {"product": "RESGABA Series", "approval_number": "DCGI/2023/12347", "date": "2023-03-10"}
    ]
}

@app.route('/')
def home():
    lang = session.get('language', 'en')
    return render_template('index.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'hi']:
        session['language'] = lang
    return redirect(request.referrer or '/')

@app.route('/about')
def about():
    lang = session.get('language', 'en')
    return render_template('about.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/contact')
def contact():
    lang = session.get('language', 'en')
    return render_template('contact.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/research')
def research():
    lang = session.get('language', 'en')
    return render_template('research.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/services')
def services():
    lang = session.get('language', 'en')
    return render_template('services.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/products')
def products():
    lang = session.get('language', 'en')
    return render_template('products.html', products=products_data, lang=lang, t=translations.get(lang, translations['en']))

@app.route('/products/<product_name>')
def product_detail(product_name):
    lang = session.get('language', 'en')
    product = products_data.get(product_name)
    return render_template("product_detail.html", product=product, lang=lang, t=translations.get(lang, translations['en'])) if product else ("Product not found", 404)

@app.route('/Gallery')
def Gallery():
    lang = session.get('language', 'en')
    return render_template('Gallery.html', lang=lang, t=translations.get(lang, translations['en']))

@app.route('/Pharmaintel_ai', methods=['GET', 'POST'])
def pharmaintel_ai():
    message, pdf_text = '', ''
    if request.method == 'POST':
        if client is None:
            message = "Error: OpenAI client is not properly initialized. Please check your API key and package versions."
        elif 'pdf_file' in request.files and request.files['pdf_file']:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename.endswith('.pdf'):
                try:
                    path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
                    pdf_file.save(path)
                    with open(path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        pdf_text = ''.join(page.extract_text() or '' for page in reader.pages)
                    os.remove(path)
                    completion = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an assistant that helps with analyzing documents and creating strategies for pharmaceutical companies."},
                            {"role": "user", "content": f"Analyze this document and create a strategy: {pdf_text}"}
                        ]
                    )
                    message = markdown.markdown(f"AI Strategy:<br>{completion.choices[0].message.content}")
                except Exception as e:
                    message = f"Error processing the PDF file: {e}"
            else:
                message = "Please upload a valid PDF file."
        elif 'openai_query' in request.form and request.form['openai_query']:
            try:
                completion = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an assistant helping with pharmaceutical strategies."},
                        {"role": "user", "content": request.form['openai_query']}
                    ]
                )
                message = markdown.markdown(f"OpenAI's Response:<br>{completion.choices[0].message.content}")
            except Exception as e:
                message = f"Error occurred while calling OpenAI: {e}"
    return render_template('Pharmaintel_ai.html', message=message, pdf_text=pdf_text)

# New Routes for Additional Features
@app.route('/product-catalog')
def product_catalog():
    lang = session.get('language', 'en')
    search_query = request.args.get('search', '')
    category = request.args.get('category', '')
    indication = request.args.get('indication', '')
    
    filtered_products = products_data.copy()
    
    if search_query:
        filtered_products = {k: v for k, v in filtered_products.items() 
                            if search_query.lower() in v.get('name', '').lower() 
                            or search_query.lower() in v.get('composition', '').lower()}
    
    if category:
        filtered_products = {k: v for k, v in filtered_products.items() 
                            if v.get('category', '').lower() == category.lower()}
    
    if indication:
        filtered_products = {k: v for k, v in filtered_products.items() 
                            if indication.lower() in v.get('indication', '').lower()}
    
    categories = list(set([p.get('category', '') for p in products_data.values() if p.get('category')]))
    indications = list(set([p.get('indication', '') for p in products_data.values() if p.get('indication')]))
    
    return render_template('product_catalog.html', 
                         products=filtered_products, 
                         all_products=products_data,
                         categories=categories,
                         indications=indications,
                         search_query=search_query,
                         selected_category=category,
                         selected_indication=indication,
                         lang=lang,
                         t=translations.get(lang, translations['en']))

@app.route('/stockist-locator')
def stockist_locator():
    lang = session.get('language', 'en')
    city = request.args.get('city', '')
    state = request.args.get('state', '')
    
    filtered_stockists = stockists_data.copy()
    
    if city:
        filtered_stockists = [s for s in filtered_stockists if city.lower() in s.get('city', '').lower()]
    
    if state:
        filtered_stockists = [s for s in filtered_stockists if state.lower() in s.get('state', '').lower()]
    
    cities = sorted(list(set([s['city'] for s in stockists_data])))
    states = sorted(list(set([s['state'] for s in stockists_data])))
    
    return render_template('stockist_locator.html', 
                         stockists=filtered_stockists,
                         all_stockists=stockists_data,
                         cities=cities,
                         states=states,
                         selected_city=city,
                         selected_state=state,
                         lang=lang,
                         t=translations.get(lang, translations['en']))

# ── Auth decorators ─────────────────────────────────────────
def doctor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'doctor_id' not in session:
            return redirect('/doctor-portal')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'tunesadmin2024')

# ── Doctor Portal ────────────────────────────────────────────
@app.route('/doctor-portal', methods=['GET', 'POST'])
def doctor_portal():
    lang = session.get('language', 'en')
    if 'doctor_id' in session:
        return redirect('/doctor-dashboard')
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if sb:
            result = sb.table('doctors').select('*').eq('username', username).eq('is_active', True).execute()
            if result.data and check_password_hash(result.data[0]['password_hash'], password):
                doc = result.data[0]
                session['doctor_id'] = doc['id']
                session['doctor_name'] = doc['name']
                return redirect('/doctor-dashboard')
            error = 'Invalid username or password.'
        else:
            if username and password:
                session['doctor_id'] = 'demo'
                session['doctor_name'] = username.title()
                return redirect('/doctor-dashboard')
            error = 'Please enter your credentials.'
    return render_template('doctor_portal.html', error=error, lang=lang, t=translations.get(lang, translations['en']))

@app.route('/doctor-logout')
def doctor_logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    return redirect('/doctor-portal')

@app.route('/doctor-dashboard')
@doctor_required
def doctor_dashboard():
    lang = session.get('language', 'en')
    papers, notifications, notif_count = [], [], 0
    doctor_id = session.get('doctor_id')
    if sb and doctor_id != 'demo':
        papers = (sb.table('papers').select('*').order('created_at', desc=True).execute()).data or []
        n = (sb.table('notifications')
               .select('*, papers(title, therapy_area)')
               .eq('doctor_id', doctor_id)
               .eq('is_read', False)
               .order('created_at', desc=True)
               .limit(10)
               .execute()).data or []
        notifications = n
        notif_count = len(n)
    return render_template('doctor_dashboard.html',
                           doctor_name=session.get('doctor_name', 'Doctor'),
                           papers=papers,
                           notifications=notifications,
                           notif_count=notif_count,
                           lang=lang)

@app.route('/doctor/notifications/read', methods=['POST'])
@doctor_required
def mark_notifications_read():
    doctor_id = session.get('doctor_id')
    if sb and doctor_id != 'demo':
        sb.table('notifications').update({'is_read': True}).eq('doctor_id', doctor_id).execute()
    return jsonify({'ok': True})

@app.route('/doctor/ai-chat', methods=['POST'])
@doctor_required
def doctor_ai_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])
    if not message:
        return jsonify({'ok': False, 'reply': 'Please type a message.'})

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        try:
            import anthropic
            ai = anthropic.Anthropic(api_key=anthropic_key)
            messages = history[-10:] + [{"role": "user", "content": message}]
            resp = ai.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=(
                    "You are a medical AI assistant for Tunes Pharma (A Division of Brinda Medicals). "
                    "You help registered doctors understand research papers, clinical guidelines, drug interactions, "
                    "dosage information, and pharmaceutical data. Be professional, concise and evidence-based. "
                    "Therapy areas: Diabetology, Neuropathy, Gastroenterology, General Medicine."
                ),
                messages=messages
            )
            return jsonify({'ok': True, 'reply': resp.content[0].text})
        except Exception as e:
            pass

    return jsonify({
        'ok': True,
        'placeholder': True,
        'reply': (
            "The AI assistant is being configured and will be live very soon. "
            "For clinical queries, please contact your Tunes Pharma medical representative."
        )
    })

# ── Admin Panel ──────────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect('/admin/papers')
    error = None
    if request.method == 'POST':
        if request.form.get('password', '') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin/papers')
        error = 'Incorrect password.'
    return render_template('admin_login.html', error=error)

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin')

@app.route('/admin/papers', methods=['GET'])
@admin_required
def admin_papers():
    papers = []
    if sb:
        papers = (sb.table('papers').select('*').order('created_at', desc=True).execute()).data or []
    return render_template('admin_papers.html', papers=papers)

@app.route('/admin/papers/upload', methods=['POST'])
@admin_required
def admin_upload_paper():
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    therapy     = request.form.get('therapy_area', 'all')
    ctype       = request.form.get('content_type', 'link')
    link_url    = request.form.get('link_url', '').strip()
    file        = request.files.get('file')
    file_url    = link_url

    if file and file.filename and sb:
        ext   = os.path.splitext(file.filename)[1].lower()
        fname = f"{uuid_lib.uuid4()}{ext}"
        tmp   = tempfile.mktemp(suffix=ext)
        file.save(tmp)
        with open(tmp, 'rb') as f:
            sb.storage.from_('papers').upload(fname, f, {'content-type': file.content_type})
        file_url = sb.storage.from_('papers').get_public_url(fname)
        ctype = 'pdf' if ext == '.pdf' else 'doc'
        try:
            os.remove(tmp)
        except Exception:
            pass

    if title and file_url and sb:
        result = sb.table('papers').insert({
            'title': title, 'description': description,
            'content_type': ctype, 'file_url': file_url,
            'therapy_area': therapy,
        }).execute()
        if result.data:
            paper_id = result.data[0]['id']
            # Fetch all active doctors with their emails
            doctors = (sb.table('doctors').select('id, name, email')
                         .eq('is_active', True).execute()).data or []
            if doctors:
                # Create in-app notification for every doctor
                sb.table('notifications').insert(
                    [{'doctor_id': d['id'], 'paper_id': paper_id} for d in doctors]
                ).execute()
                # Send email to every doctor who has an email address
                for doc in doctors:
                    if doc.get('email'):
                        send_email_notification(
                            doctor_email   = doc['email'],
                            doctor_name    = doc['name'],
                            paper_title    = title,
                            paper_description = description,
                            paper_url      = file_url,
                            therapy_area   = therapy
                        )
    return redirect('/admin/papers')

@app.route('/admin/papers/delete/<paper_id>', methods=['POST'])
@admin_required
def admin_delete_paper(paper_id):
    if sb:
        sb.table('papers').delete().eq('id', paper_id).execute()
    return redirect('/admin/papers')

@app.route('/admin/doctors', methods=['GET'])
@admin_required
def admin_doctors():
    doctors = []
    if sb:
        doctors = (sb.table('doctors').select('*').order('created_at', desc=True).execute()).data or []
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctors/add', methods=['POST'])
@admin_required
def admin_add_doctor():
    name      = request.form.get('name', '').strip()
    username  = request.form.get('username', '').strip()
    password  = request.form.get('password', '').strip()
    email     = request.form.get('email', '').strip()
    phone     = request.form.get('phone', '').strip()
    hospital  = request.form.get('hospital', '').strip()
    specialty = request.form.get('specialty', '').strip()
    if name and username and password and sb:
        sb.table('doctors').insert({
            'name': name, 'username': username,
            'password_hash': generate_password_hash(password),
            'email': email, 'phone': phone,
            'hospital': hospital, 'specialty': specialty,
        }).execute()
    return redirect('/admin/doctors')

@app.route('/admin/doctors/toggle/<doctor_id>', methods=['POST'])
@admin_required
def admin_toggle_doctor(doctor_id):
    if sb:
        doc = (sb.table('doctors').select('is_active').eq('id', doctor_id).execute()).data
        if doc:
            sb.table('doctors').update({'is_active': not doc[0]['is_active']}).eq('id', doctor_id).execute()
    return redirect('/admin/doctors')

@app.route('/admin/doctors/delete/<doctor_id>', methods=['POST'])
@admin_required
def admin_delete_doctor(doctor_id):
    if sb:
        sb.table('doctors').delete().eq('id', doctor_id).execute()
    return redirect('/admin/doctors')

@app.route('/regulatory-compliance')
def regulatory_compliance():
    lang = session.get('language', 'en')
    return render_template('regulatory_compliance.html', regulatory_data=regulatory_data, lang=lang, t=translations.get(lang, translations['en']))

@app.route('/online-ordering', methods=['GET', 'POST'])
def online_ordering():
    lang = session.get('language', 'en')
    if request.method == 'POST':
        # Handle order submission
        order_data = {
            'name': request.form.get('name'),
            'company': request.form.get('company'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'products': request.form.getlist('products'),
            'quantities': request.form.getlist('quantities')
        }
        return render_template('order_confirmation.html', order=order_data, lang=lang, t=translations.get(lang, translations['en']))
    
    return render_template('online_ordering.html', products=products_data, lang=lang, t=translations.get(lang, translations['en']))

@app.route('/admin/debug')
@admin_required
def admin_debug():
    """Quick health check — shows what's connected and what's missing."""
    checks = {}
    # Supabase
    checks['supabase_url']  = '✅ Set' if os.getenv('SUPABASE_URL')         else '❌ Missing env var: SUPABASE_URL'
    checks['supabase_key']  = '✅ Set' if os.getenv('SUPABASE_SERVICE_KEY') else '❌ Missing env var: SUPABASE_SERVICE_KEY'
    checks['supabase_conn'] = '✅ Connected' if sb else '❌ Not connected (check URL and key)'
    # Gmail
    checks['gmail_user']    = '✅ Set' if os.getenv('GMAIL_USER')        else '❌ Missing env var: GMAIL_USER'
    checks['gmail_pass']    = '✅ Set' if os.getenv('GMAIL_APP_PASSWORD') else '❌ Missing env var: GMAIL_APP_PASSWORD'
    # Admin password
    checks['admin_pass']    = '✅ Custom' if os.getenv('ADMIN_PASSWORD') else '⚠️  Using default (set ADMIN_PASSWORD env var)'
    # AI
    checks['anthropic_key'] = '✅ Set (AI active)' if os.getenv('ANTHROPIC_API_KEY') else '⚠️  Not set (AI shows placeholder)'
    # DB counts
    if sb:
        try:
            checks['doctors_count'] = str(len((sb.table('doctors').select('id').execute()).data or []))  + ' doctors in DB'
            checks['papers_count']  = str(len((sb.table('papers').select('id').execute()).data or []))   + ' papers in DB'
            checks['notif_count']   = str(len((sb.table('notifications').select('id').execute()).data or [])) + ' notifications in DB'
        except Exception as e:
            checks['db_error'] = f'❌ DB query failed: {e} — Did you run schema.sql in Supabase?'
    rows = ''.join(f'<tr><td style="padding:10px 16px;font-weight:600;color:#0f1e2d;white-space:nowrap">{k}</td><td style="padding:10px 16px;color:#374151">{v}</td></tr>' for k, v in checks.items())
    return f'''<!DOCTYPE html><html><head><title>Debug | Tunes Pharma Admin</title>
    <style>body{{font-family:sans-serif;padding:40px;background:#f5f7fb}}
    h1{{color:#0f1e2d}}table{{background:#fff;border-radius:12px;border-collapse:collapse;width:100%;max-width:680px;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
    tr{{border-bottom:1px solid #f0f2f5}}td{{font-size:14px}}
    a{{color:#1e6ff1;display:block;margin-top:20px;font-size:14px}}</style></head>
    <body><h1>🔍 System Health Check</h1>
    <table>{rows}</table>
    <a href="/admin/papers">← Back to Admin</a></body></html>'''

if __name__ == "__main__":
    app.run(debug=True)
