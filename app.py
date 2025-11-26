from flask import Flask, render_template, request, session
from openai import OpenAI
import markdown, PyPDF2, os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change in production
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

# Initialize OpenAI client
# Get API key from environment variable or use default (for development only)
api_key = os.getenv('OPENAI_API_KEY', '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')

try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"Warning: Could not initialize OpenAI client: {e}")
    print("The app will run but AI features will not be available.")
    client = None

products_data = {
    "ecoglim-mv1": {
        "name": "Ecoglim MV1",
        "description": "Ecoglim MV 1mg/500mg/0.2mg Tablet SR is used to control blood sugar levels in adults with type 2 diabetes...",
        "image": "ecoglim-mv1.jpg",
        "price": "₹78.57",
        "features": "Metformin + Multi-vitamin Complex",
        "benefits": "Enhances overall health and improves glycemic control in diabetic patients.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd.",
        "category": "Diabetic",
        "composition": "Glimepiride 1mg + Metformin 500mg + Methylcobalamin 0.2mg",
        "indication": "Type 2 Diabetes",
        "schedule": "H"
    },
    "ecoglim-mv2": {
        "name": "Ecoglim MV2",
        "description": "Advanced diabetes management with enhanced formulation",
        "image": "ecoglim-mv2.jpg",
        "price": "₹85.00",
        "category": "Diabetic",
        "composition": "Glimepiride 2mg + Metformin 500mg + Methylcobalamin 0.2mg",
        "indication": "Type 2 Diabetes",
        "schedule": "H"
    },
    "nactaid": {
        "name": "NACTAID",
        "description": "Comprehensive therapeutic solution for optimal patient outcomes",
        "image": "nactaid.jpg",
        "price": "₹120.00",
        "category": "Diabetic",
        "composition": "Nateglinide + Metformin",
        "indication": "Type 2 Diabetes",
        "schedule": "H"
    },
    "resgaba-nt": {
        "name": "RESGABA-NT",
        "description": "Neuropathic pain management",
        "image": "resgaba-nt.jpg",
        "price": "₹150.00",
        "category": "Ortho",
        "composition": "Gabapentin + Nortriptyline",
        "indication": "Neuropathic Pain",
        "schedule": "H"
    },
    "resgaba-dlx": {
        "name": "RESGABA-DLX",
        "description": "Advanced pain management solution",
        "image": "resgaba-dlx.jpg",
        "price": "₹180.00",
        "category": "Ortho",
        "composition": "Gabapentin + Duloxetine",
        "indication": "Neuropathic Pain",
        "schedule": "H"
    },
    "rabishir-dsr": {
        "name": "RABISHIR-DSR",
        "description": "Gastrointestinal disorder treatment",
        "image": "rabishir-dsr.jpg",
        "price": "₹95.00",
        "category": "Gastro",
        "composition": "Rabeprazole + Domperidone",
        "indication": "GERD, Gastric Disorders",
        "schedule": "H"
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
    return request.referrer or '/'

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
