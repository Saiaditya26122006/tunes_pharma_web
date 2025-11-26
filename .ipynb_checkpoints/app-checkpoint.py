from flask import Flask, render_template, request
from openai import OpenAI
import markdown, PyPDF2, os

client = OpenAI(api_key="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")
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

products_data = {
    "ecoglim-mv1": {
        "name": "Ecoglim MV1",
        "description": "Ecoglim MV 1mg/500mg/0.2mg Tablet SR is used to control blood sugar levels in adults with type 2 diabetes...",
        "image": "ecoglim-mv1.jpg",
        "price": "₹78.57",
        "features": "Metformin + Multi-vitamin Complex",
        "benefits": "Enhances overall health and improves glycemic control in diabetic patients.",
        "manufacturer": "Tunes Therapeutics Pvt. Ltd."
    },

}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/research')
def research():
    return render_template('research.html')

@app.route('/products')
def products():
    return render_template('products.html', products=products_data)

@app.route('/products/<product_name>')
def product_detail(product_name):
    product = products_data.get(product_name)
    return render_template("product_detail.html", product=product) if product else ("Product not found", 404)
@app.route('/Gallery')
def Gallery():
    return render_template('Gallery.html')

@app.route('/Pharmaintel_ai', methods=['GET', 'POST'])
def pharmaintel_ai():
    message, pdf_text = '', ''
    if request.method == 'POST':
        if 'pdf_file' in request.files and request.files['pdf_file']:
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

if __name__ == "__main__":
    app.run(debug=True)
