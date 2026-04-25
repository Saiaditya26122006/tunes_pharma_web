from flask import Flask, render_template, request, session, redirect
import os

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
        "name": "Ecoglim MV1",
        "description": "Ecoglim MV1 is a sustained-release triple-combination tablet used to control blood sugar levels in adults with Type 2 diabetes. It combines an insulin secretagogue, a biguanide, and a neuroprotective vitamin for comprehensive glycemic and nerve health management.",
        "image": "ecoglim-mv1.jpg",
        "features": "Glimepiride + Metformin SR + Methylcobalamin",
        "benefits": "Stimulates pancreatic insulin secretion, reduces hepatic glucose production, and supports peripheral nerve health through Methylcobalamin supplementation.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Diabetic",
        "composition": "Glimepiride 1mg + Metformin Hydrochloride SR 500mg + Methylcobalamin 0.2mg",
        "indication": "Type 2 Diabetes Mellitus with peripheral neuropathy risk",
        "how_to_use": "Take once daily with or just before a meal, preferably at the same time each day. Swallow whole — do not crush or chew.",
        "side_effects": "Hypoglycaemia, nausea, vomiting, diarrhoea, dizziness, headache. Rarely: lactic acidosis (discontinue if suspected).",
        "storage": "Store below 30°C in a dry place away from direct sunlight. Keep out of reach of children.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
    },
    "ecoglim-mv2": {
        "name": "Ecoglim-MV2",
        "description": "Ecoglim-MV2 is a triple-action antidiabetic tablet combining Glimepiride, Metformin Hydrochloride SR and Voglibose. It delivers simultaneous control of fasting and post-prandial blood glucose through three distinct mechanisms.",
        "image": "ecoglim-mv2.jpg",
        "features": "Glimepiride + Metformin SR + Voglibose",
        "benefits": "Stimulates insulin secretion, suppresses hepatic glucose output, and blocks intestinal alpha-glucosidase to reduce post-meal glucose spikes.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Diabetic",
        "composition": "Glimepiride 2mg + Metformin Hydrochloride SR 500mg + Voglibose 0.2mg",
        "indication": "Type 2 Diabetes Mellitus — particularly with post-prandial hyperglycaemia",
        "how_to_use": "Take once daily with the first bite of a main meal. Do not skip meals. Swallow whole.",
        "side_effects": "Hypoglycaemia, flatulence, abdominal distension, diarrhoea, nausea. GI side effects usually reduce with continued use.",
        "storage": "Store below 30°C in a dry place away from direct sunlight.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
    },
    "ecoglim-mp1": {
        "name": "Ecoglim-MPI",
        "description": "Ecoglim-MPI is a prolonged-release antidiabetic combination of Metformin Hydrochloride, Glimepiride and Pioglitazone. It targets three key pathways of Type 2 diabetes — insulin resistance, hepatic glucose production and pancreatic insulin secretion.",
        "image": "ecoglim-mp1.jpg",
        "features": "Metformin PR + Glimepiride 1mg + Pioglitazone 15mg",
        "benefits": "Reduces insulin resistance (Pioglitazone), decreases hepatic glucose output (Metformin), and stimulates insulin secretion (Glimepiride) for comprehensive HbA1c reduction.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Diabetic",
        "composition": "Metformin Hydrochloride PR 500mg + Glimepiride 1mg + Pioglitazone 15mg",
        "indication": "Type 2 Diabetes Mellitus with significant insulin resistance",
        "how_to_use": "Take once daily with or just after a meal. Prolonged-release formulation — do not crush or chew. Swallow whole.",
        "side_effects": "Hypoglycaemia, fluid retention (oedema), weight gain, nausea, diarrhoea. Monitor for signs of heart failure in at-risk patients.",
        "storage": "Store below 30°C in a dry place. Protect from moisture.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
    },
    "ecoglim-mp2": {
        "name": "Ecoglim MP2",
        "description": "Ecoglim MP2 is a higher-strength prolonged-release antidiabetic tablet containing Metformin Hydrochloride, Glimepiride 2mg and Pioglitazone. Designed for patients needing more aggressive glycemic control with pronounced insulin resistance.",
        "image": "ecoglim-mp2.jpg",
        "features": "Metformin PR + Glimepiride 2mg + Pioglitazone 15mg",
        "benefits": "Enhanced triple-action antidiabetic effect — superior HbA1c reduction, improved insulin sensitivity, and reduced fasting glucose in advanced Type 2 diabetes.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Diabetic",
        "composition": "Metformin Hydrochloride PR 500mg + Glimepiride 2mg + Pioglitazone 15mg",
        "indication": "Type 2 Diabetes Mellitus with marked insulin resistance requiring escalated therapy",
        "how_to_use": "Take once daily with or just after a meal. Do not crush or chew. Swallow whole with water.",
        "side_effects": "Hypoglycaemia, peripheral oedema, weight gain, nausea, abdominal discomfort. Caution in patients with cardiac disease.",
        "storage": "Store below 30°C in a dry place. Protect from moisture and light.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
    },
    "nactaid": {
        "name": "NACTaid",
        "description": "NACTaid is a combination of N-Acetylcysteine (NAC) and Taurine that provides powerful antioxidant, hepatoprotective and mucolytic benefits. NAC replenishes glutathione — the body's primary antioxidant — while Taurine supports cellular membrane stability and cardiovascular health.",
        "image": "nactaid.jpg",
        "features": "N-Acetylcysteine 600mg + Taurine 500mg",
        "benefits": "Replenishes glutathione stores, protects liver cells from oxidative damage, thins respiratory mucus, and supports cardiovascular function through Taurine's osmoregulatory and antioxidant properties.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Metabolic",
        "composition": "N-Acetylcysteine 600mg + Taurine 500mg",
        "indication": "Oxidative stress, hepatoprotection, mucolytic therapy, metabolic wellness, acetaminophen toxicity adjunct",
        "how_to_use": "Take one tablet twice daily after meals, or as directed by the physician. Adequate hydration recommended.",
        "side_effects": "Generally well tolerated. Mild nausea, vomiting or rash may occur. Rarely: bronchospasm in sensitive patients.",
        "storage": "Store below 25°C in a dry place. Protect from moisture and light.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
    },
    "resgaba-nt": {
        "name": "Resgaba-NT",
        "description": "Resgaba-NT is a triple-combination capsule of Pregabalin, Nortriptyline and Mecobalamin designed for comprehensive neuropathic pain management. It targets the pain signalling pathway, the descending inhibitory pain system, and peripheral nerve regeneration simultaneously.",
        "image": "resgaba-nt.jpg",
        "features": "Pregabalin 75mg + Nortriptyline 10mg + Mecobalamin 1500mcg",
        "benefits": "Pregabalin reduces neuronal hyperexcitability; Nortriptyline enhances descending pain inhibition and improves sleep; Mecobalamin (active B12) promotes myelin sheath regeneration for long-term nerve repair.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Ortho",
        "composition": "Pregabalin 75mg + Nortriptyline 10mg + Mecobalamin 1500mcg",
        "indication": "Diabetic peripheral neuropathy, post-herpetic neuralgia, fibromyalgia, nerve injury pain",
        "how_to_use": "Take one capsule at bedtime or as directed by the physician. Do not discontinue abruptly — taper under medical supervision.",
        "side_effects": "Dizziness, somnolence, dry mouth, constipation, blurred vision, weight gain. Caution when driving or operating machinery.",
        "storage": "Store below 30°C in a dry place away from direct sunlight.",
        "schedule": "H",
        "packing": "10×10 Tablets (Alu-Alu)"
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
        "name": "RABISHIR-DSR",
        "description": "RABISHIR-DSR is a dual-release capsule combining Rabeprazole (proton pump inhibitor) with Domperidone SR (prokinetic) to provide superior acid suppression alongside improved gastric emptying and motility — addressing both acid-related and motility-related GI disorders.",
        "image": "rabishir-dsr.jpg",
        "features": "Rabeprazole 20mg + Domperidone 30mg SR",
        "benefits": "Rabeprazole rapidly and potently suppresses gastric acid secretion; Domperidone SR enhances gastric motility, reduces nausea and prevents reflux — together providing long-lasting symptom relief.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Gastro",
        "composition": "Rabeprazole Sodium 20mg + Domperidone 30mg SR",
        "indication": "GERD, gastritis, peptic ulcer disease, symptomatic GERD with nausea, functional dyspepsia",
        "how_to_use": "Take one capsule 30 minutes before breakfast, or as directed by the physician. Swallow whole — do not crush.",
        "side_effects": "Headache, diarrhoea, abdominal pain, dry mouth. Rarely: QT prolongation with Domperidone (avoid in cardiac patients).",
        "storage": "Store below 30°C in a dry place. Protect from moisture.",
        "schedule": "H",
        "packing": "10×10 Capsules (Alu-Alu)"
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

@app.route('/doctor-portal', methods=['GET', 'POST'])
def doctor_portal():
    lang = session.get('language', 'en')
    if request.method == 'POST':
        # Simple login check (in production, use proper authentication)
        email = request.form.get('email')
        password = request.form.get('password')
        # For demo purposes, any email/password works
        if email and password:
            return render_template('doctor_dashboard.html', doctor_email=email, lang=lang, t=translations.get(lang, translations['en']))
    
    return render_template('doctor_portal.html', lang=lang, t=translations.get(lang, translations['en']))

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

if __name__ == "__main__":
    app.run(debug=True)
