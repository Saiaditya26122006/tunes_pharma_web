"""Public website routes — no authentication required.

All original URLs are preserved exactly.
"""

import os
import tempfile
from flask import Blueprint, render_template, request, session, redirect, jsonify

from app.extensions import sb, openai_client

public_bp = Blueprint('public', __name__)

# ---------------------------------------------------------------------------
# Lazy import of data dicts that still live in the old app.py module scope.
# After the refactor, app.py re-exports them; we import at call time to
# avoid circular imports during blueprint registration.
# ---------------------------------------------------------------------------

def _get_data():
    from app_data import products_data, stockists_data, regulatory_data, translations
    return products_data, stockists_data, regulatory_data, translations


def _lang():
    _, _, _, translations = _get_data()
    lang = session.get('language', 'en')
    return lang, translations.get(lang, translations['en'])


# ── Core pages ─────────────────────────────────────────────────

@public_bp.route('/')
def home():
    lang, t = _lang()
    return render_template('index.html', lang=lang, t=t)


@public_bp.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'hi']:
        session['language'] = lang
    return redirect(request.referrer or '/')


@public_bp.route('/about')
def about():
    lang, t = _lang()
    return render_template('about.html', lang=lang, t=t)


@public_bp.route('/contact')
def contact():
    lang, t = _lang()
    return render_template('contact.html', lang=lang, t=t)


@public_bp.route('/research')
def research():
    lang, t = _lang()
    return render_template('research.html', lang=lang, t=t)


@public_bp.route('/services')
def services():
    lang, t = _lang()
    return render_template('services.html', lang=lang, t=t)


@public_bp.route('/products')
def products():
    products_data, _, _, translations = _get_data()
    lang, t = _lang()
    return render_template('products.html', products=products_data, lang=lang, t=t)


@public_bp.route('/products/<product_name>')
def product_detail(product_name):
    products_data, _, _, _ = _get_data()
    lang, t = _lang()
    product = products_data.get(product_name)
    if not product:
        return "Product not found", 404
    return render_template("product_detail.html", product=product, lang=lang, t=t)


@public_bp.route('/gallery')
def gallery():
    lang, t = _lang()
    return render_template('Gallery.html', lang=lang, t=t)


@public_bp.route('/Gallery')
def gallery_redirect():
    return redirect('/gallery', code=308)


@public_bp.route('/Pharmaintel_ai')
def pharmaintel_ai_redirect():
    return redirect('/pharmaintel_ai', code=308)


@public_bp.route('/pharmaintel_ai', methods=['GET', 'POST'])
def pharmaintel_ai():
    message, pdf_text = '', ''
    if request.method == 'POST':
        if openai_client is None:
            message = "Error: OpenAI client is not properly initialized. Please check your API key and package versions."
        elif 'pdf_file' in request.files and request.files['pdf_file']:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename.endswith('.pdf'):
                try:
                    from flask import current_app
                    import PyPDF2, markdown
                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_file.filename)
                    pdf_file.save(path)
                    with open(path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        pdf_text = ''.join(page.extract_text() or '' for page in reader.pages)
                    os.remove(path)
                    completion = openai_client.chat.completions.create(
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
                import markdown
                completion = openai_client.chat.completions.create(
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


# ── Product catalog & stockist locator ─────────────────────────

@public_bp.route('/product-catalog')
def product_catalog():
    products_data, _, _, _ = _get_data()
    lang, t = _lang()
    search_query = request.args.get('search', '')
    category = request.args.get('category', '')
    indication = request.args.get('indication', '')

    filtered = products_data.copy()
    if search_query:
        filtered = {k: v for k, v in filtered.items()
                    if search_query.lower() in v.get('name', '').lower()
                    or search_query.lower() in v.get('composition', '').lower()}
    if category:
        filtered = {k: v for k, v in filtered.items()
                    if v.get('category', '').lower() == category.lower()}
    if indication:
        filtered = {k: v for k, v in filtered.items()
                    if indication.lower() in v.get('indication', '').lower()}

    categories = list(set(p.get('category', '') for p in products_data.values() if p.get('category')))
    indications = list(set(p.get('indication', '') for p in products_data.values() if p.get('indication')))

    return render_template('product_catalog.html',
                           products=filtered, all_products=products_data,
                           categories=categories, indications=indications,
                           search_query=search_query, selected_category=category,
                           selected_indication=indication, lang=lang, t=t)


@public_bp.route('/stockist-locator')
def stockist_locator():
    _, stockists_data, _, _ = _get_data()
    lang, t = _lang()
    city = request.args.get('city', '')
    state = request.args.get('state', '')

    filtered = stockists_data.copy()
    if city:
        filtered = [s for s in filtered if city.lower() in s.get('city', '').lower()]
    if state:
        filtered = [s for s in filtered if state.lower() in s.get('state', '').lower()]

    cities = sorted(set(s['city'] for s in stockists_data))
    states = sorted(set(s['state'] for s in stockists_data))

    return render_template('stockist_locator.html',
                           stockists=filtered, all_stockists=stockists_data,
                           cities=cities, states=states,
                           selected_city=city, selected_state=state, lang=lang, t=t)


# ── Academic Insights (public) ─────────────────────────────────

@public_bp.route('/academic-insights')
def academic_insights():
    articles = []
    if sb:
        try:
            articles = (sb.table('papers')
                        .select('*')
                        .eq('status', 'published')
                        .order('published_at', desc=True)
                        .execute()).data or []
        except Exception:
            pass
    lang, t = _lang()
    return render_template('academic_insights.html', articles=articles, lang=lang, t=t)


# ── Regulatory / ordering ──────────────────────────────────────

@public_bp.route('/regulatory-compliance')
def regulatory_compliance():
    _, _, regulatory_data, _ = _get_data()
    lang, t = _lang()
    return render_template('regulatory_compliance.html', regulatory_data=regulatory_data, lang=lang, t=t)


@public_bp.route('/online-ordering', methods=['GET', 'POST'])
def online_ordering():
    products_data, _, _, _ = _get_data()
    lang, t = _lang()
    if request.method == 'POST':
        order_data = {
            'name': request.form.get('name'),
            'company': request.form.get('company'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'products': request.form.getlist('products'),
            'quantities': request.form.getlist('quantities'),
        }
        return render_template('order_confirmation.html', order=order_data, lang=lang, t=t)
    return render_template('online_ordering.html', products=products_data, lang=lang, t=t)


# ── SEO ────────────────────────────────────────────────────────

@public_bp.route('/robots.txt')
def robots_txt():
    from flask import current_app
    base = current_app.config['BASE_URL']
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /set-language/\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@public_bp.route('/sitemap.xml')
def sitemap_xml():
    from flask import current_app
    products_data, _, _, _ = _get_data()
    base = current_app.config['BASE_URL']
    paths = [
        '/', '/about', '/contact', '/research', '/services',
        '/products', '/gallery', '/pharmaintel_ai',
        '/product-catalog', '/stockist-locator',
        '/regulatory-compliance', '/online-ordering',
    ]
    paths += [f'/products/{slug}' for slug in products_data.keys()]
    urls = ''.join(f'<url><loc>{base}{p}</loc></url>' for p in paths)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}
