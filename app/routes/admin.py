"""Admin panel routes — session-based authentication.

Supports both the new admin_users table and the legacy ADMIN_PASSWORD
during the migration period.  Once all admin accounts are created, the
legacy path can be removed.
"""

import os
import smtplib
import tempfile
import uuid as uuid_lib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (Blueprint, render_template, request, session,
                   redirect, jsonify, flash, current_app)
from werkzeug.security import generate_password_hash

from app.extensions import sb, wa
from app.middleware.auth import admin_required
from app.services import notification_service, ai_service
from app.services.auth_service import authenticate_admin, check_rate_limit

admin_bp = Blueprint('admin', __name__)

# ── System prompts (moved from app.py, unchanged) ─────────────

DOSE_CALC_SYSTEM = (
    "You are a clinical pharmacology assistant for Tunes Pharma. "
    "You help licensed physicians with dose calculations at the point of care.\n\n"
    "Tunes Pharma products:\n"
    "- Ecoglim MV (Glimepiride+Metformin+Voglibose, 1mg/500mg/0.2mg or 2mg/500mg/0.2mg) — Type 2 Diabetes\n"
    "- Ecoglim MP (Glimepiride+Metformin+Pioglitazone, 1mg/500mg/15mg or 2mg/500mg/15mg) — Type 2 Diabetes\n"
    "- Nactaid (Taurine 500mg + Acetylcysteine 150mg) — Chronic Kidney Disease\n"
    "- Resgaba NT (Pregabalin 75mg + Nortriptyline 10mg + Methylcobalamin 1500mcg) — Neuropathic Pain\n"
    "- Resgaba DLX (Pregabalin 75mg + Duloxetine 30mg) — Neuropathic Pain / Anxiety\n"
    "- Rabishir D (Domperidone 30mg + Rabeprazole 20mg) — GERD / Acid Reflux\n\n"
    "Respond in this exact format:\n"
    "**DOSE:** [standard adult dose and frequency]\n"
    "**ADJUSTMENTS:** [modifications for the patient's weight, age, or conditions — be specific]\n"
    "**DURATION:** [typical treatment duration]\n"
    "**WARNINGS:** [key clinical warnings — monitoring, contraindications, interactions to watch]\n"
    "**TUNES PHARMA:** [if a Tunes Pharma product is appropriate, name it and relevant strength. "
    "If not applicable, write: Not applicable for this drug.]\n\n"
    "Be precise, evidence-based, and concise. You are supporting a licensed physician."
)

INTERACTION_SYSTEM = (
    "You are a drug interaction specialist for Tunes Pharma. "
    "You help licensed physicians check drug interactions at the point of care.\n\n"
    "For each pair of drugs, use this format:\n"
    "**[Drug A] + [Drug B]**\n"
    "Severity: 🟢 SAFE / 🟡 CAUTION / 🔴 AVOID\n"
    "Mechanism: [brief explanation]\n"
    "Clinical action: [what the doctor should do]\n\n"
    "List all pairs starting with the most severe. Then end with:\n"
    "**OVERALL:** SAFE TO CO-PRESCRIBE / PRESCRIBE WITH MONITORING / AVOID COMBINATION\n\n"
    "If a safer alternative exists from Tunes Pharma products (Ecoglim MV, Ecoglim MP, Nactaid, "
    "Resgaba NT, Resgaba DLX, Rabishir D), mention it. Be evidence-based and concise."
)

CONTENT_GEN_SYSTEM = (
    "You are a professional medical communications writer for Tunes Pharma.\n\n"
    "Tunes Pharma products:\n"
    "- Ecoglim MV and Ecoglim MP: Antidiabetic combinations (Glimepiride + Metformin + Voglibose or Pioglitazone)\n"
    "- Nactaid: Antioxidant for Chronic Kidney Disease (Taurine + Acetylcysteine)\n"
    "- Resgaba NT and Resgaba DLX: Neuropathic pain relief (Pregabalin combinations)\n"
    "- Rabishir D: GERD treatment (Domperidone + Rabeprazole)\n\n"
    "Writing rules:\n"
    "1. Professional but warm tone — not corporate jargon\n"
    "2. Under 200 words unless asked otherwise\n"
    "3. Use {{Doctor_Name}} as the doctor name placeholder\n"
    "4. Sign off: Warm regards,\\nTeam Tunes Pharma | Vijayawada\n"
    "5. Only make clinically accurate claims within approved indications\n"
    "6. First line must be: Subject: [subject here] — then a blank line — then the message body\n"
    "7. Write only the message. No meta-commentary."
)


# ── Auth ───────────────────────────────────────────────────────

@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin') or session.get('admin_user_id'):
        return redirect('/admin/dashboard')

    error = None
    if request.method == 'POST':
        # Rate limiting
        ip = request.remote_addr or 'unknown'
        if not check_rate_limit(ip, 'admin_login', 5, 300):
            error = 'Too many login attempts. Please try again in a few minutes.'
            return render_template('admin_login.html', error=error)

        email_or_password = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # Try new admin_users table first
        if email_or_password and password:
            admin = authenticate_admin(email_or_password, password)
            if admin:
                session['is_admin'] = True
                session['admin_user_id'] = admin['id']
                session['admin_name'] = admin.get('name', '')
                session['admin_role'] = admin.get('role', 'admin')
                return redirect('/admin/dashboard')

        # Legacy fallback: single shared password
        legacy_pw = current_app.config.get('LEGACY_ADMIN_PASSWORD')
        submitted_pw = password or email_or_password
        if legacy_pw and submitted_pw == legacy_pw:
            session['is_admin'] = True
            return redirect('/admin/dashboard')

        error = 'Invalid credentials.'

    return render_template('admin_login.html', error=error)


@admin_bp.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_user_id', None)
    session.pop('admin_name', None)
    session.pop('admin_role', None)
    return redirect('/admin')


# ── Dashboard ──────────────────────────────────────────────────

@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = {
        'total_articles': 0, 'published_articles': 0, 'draft_articles': 0,
        'archived_articles': 0, 'total_doctors': 0, 'active_doctors': 0,
        'inactive_doctors': 0, 'total_notifications_sent': 0,
        'recent_articles': [], 'recent_notifications': [],
    }
    if sb:
        try:
            all_papers = (sb.table('papers').select('*').order('created_at', desc=True).execute()).data or []
            stats['total_articles'] = len(all_papers)
            stats['published_articles'] = len([p for p in all_papers if p.get('status') == 'published'])
            stats['draft_articles'] = len([p for p in all_papers if p.get('status') == 'draft'])
            stats['archived_articles'] = len([p for p in all_papers if p.get('status') == 'archived'])
            stats['recent_articles'] = all_papers[:5]

            all_doctors = (sb.table('doctors').select('*').execute()).data or []
            stats['total_doctors'] = len(all_doctors)
            stats['active_doctors'] = len([d for d in all_doctors if d.get('is_active')])
            stats['inactive_doctors'] = stats['total_doctors'] - stats['active_doctors']

            try:
                all_notifs = (sb.table('notification_campaigns').select('*').order('created_at', desc=True).limit(10).execute()).data or []
                stats['recent_notifications'] = all_notifs
                stats['total_notifications_sent'] = len((sb.table('notification_campaigns').select('id').execute()).data or [])
            except Exception:
                # Fall back to legacy table
                try:
                    all_notifs = (sb.table('whatsapp_messages').select('*').order('created_at', desc=True).limit(10).execute()).data or []
                    stats['recent_notifications'] = all_notifs
                    stats['total_notifications_sent'] = len((sb.table('whatsapp_messages').select('id').execute()).data or [])
                except Exception:
                    pass
        except Exception as e:
            current_app.logger.error(f"[Dashboard] Error loading stats: {e}")
    return render_template('admin_dashboard.html', stats=stats)


# ── Paper management ───────────────────────────────────────────

@admin_bp.route('/admin/papers', methods=['GET'])
@admin_required
def admin_papers():
    papers = []
    status_filter = request.args.get('status', '')
    if sb:
        q = sb.table('papers').select('*').order('created_at', desc=True)
        if status_filter in ('draft', 'published', 'archived'):
            q = q.eq('status', status_filter)
        papers = (q.execute()).data or []
    return render_template('admin_papers.html', papers=papers, current_filter=status_filter)


@admin_bp.route('/admin/papers/upload', methods=['POST'])
@admin_required
def admin_upload_paper():
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    therapy     = request.form.get('therapy_area', 'all')
    ctype       = request.form.get('content_type', 'link')
    status      = request.form.get('status', 'draft')
    author      = request.form.get('author', '').strip()
    category    = request.form.get('category', 'General').strip()
    link_url    = request.form.get('link_url', '').strip()
    file        = request.files.get('file')
    thumbnail   = request.files.get('thumbnail')
    file_url    = link_url
    thumbnail_url = None

    if file and file.filename and sb:
        ext = os.path.splitext(file.filename)[1].lower()
        fname = f"{uuid_lib.uuid4()}{ext}"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        file.save(tmp)
        try:
            with open(tmp, 'rb') as f:
                sb.storage.from_('papers').upload(fname, f, {'content-type': file.content_type})
            file_url = sb.storage.from_('papers').get_public_url(fname)
            ctype = 'pdf' if ext == '.pdf' else 'doc'
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    if thumbnail and thumbnail.filename and sb:
        ext = os.path.splitext(thumbnail.filename)[1].lower() or '.jpg'
        tname = f"thumb_{uuid_lib.uuid4()}{ext}"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        thumbnail.save(tmp)
        try:
            with open(tmp, 'rb') as f:
                sb.storage.from_('papers').upload(tname, f, {'content-type': thumbnail.content_type})
            thumbnail_url = sb.storage.from_('papers').get_public_url(tname)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    if title and file_url and sb:
        insert_data = {
            'title': title, 'description': description,
            'content_type': ctype, 'file_url': file_url,
            'therapy_area': therapy, 'status': status,
            'author': author, 'category': category,
        }
        if thumbnail_url:
            insert_data['thumbnail_url'] = thumbnail_url
        if status == 'published':
            insert_data['published_at'] = datetime.now(timezone.utc).isoformat()

        result = sb.table('papers').insert(insert_data).execute()
        if result.data:
            paper = result.data[0]
            paper_id = paper['id']
            doctors = (sb.table('doctors')
                       .select('id, name, email, whatsapp_number, whatsapp_consent')
                       .eq('is_active', True).execute()).data or []

            if status == 'published' and doctors:
                sb.table('notifications').insert(
                    [{'doctor_id': d['id'], 'paper_id': paper_id} for d in doctors]
                ).execute()

                for doc in doctors:
                    if doc.get('email'):
                        notification_service.send_email_notification(
                            doctor_email=doc['email'], doctor_name=doc['name'],
                            paper_title=title, paper_description=description,
                            paper_url=file_url, therapy_area=therapy,
                        )

                if notification_service.is_whatsapp_configured():
                    eligible = [d for d in doctors if d.get('whatsapp_consent') and d.get('whatsapp_number')]
                    if eligible:
                        wa_result = notification_service.broadcast_whatsapp(eligible, paper)
                        if wa_result:
                            _log_whatsapp_campaign(
                                sb, message_type='article_notification',
                                paper_id=paper_id, message_body=f"Article: {title}",
                                results=wa_result,
                            )

    return redirect('/admin/dashboard')


@admin_bp.route('/admin/papers/<paper_id>', methods=['GET'])
@admin_required
def admin_get_paper(paper_id):
    if sb:
        result = sb.table('papers').select('*').eq('id', paper_id).execute()
        if result.data:
            return jsonify(result.data[0])
    return jsonify({}), 404


@admin_bp.route('/admin/papers/edit/<paper_id>', methods=['POST'])
@admin_required
def admin_edit_paper(paper_id):
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    therapy     = request.form.get('therapy_area', 'all')
    status      = request.form.get('status', 'draft')
    author      = request.form.get('author', '').strip()
    category    = request.form.get('category', 'General').strip()
    link_url    = request.form.get('link_url', '').strip()
    file        = request.files.get('file')
    thumbnail   = request.files.get('thumbnail')

    if not (title and sb):
        return redirect('/admin/papers')

    update_data = {
        'title': title, 'description': description, 'therapy_area': therapy,
        'status': status, 'author': author, 'category': category,
    }
    if status == 'published':
        update_data['published_at'] = datetime.now(timezone.utc).isoformat()

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        fname = f"{uuid_lib.uuid4()}{ext}"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        file.save(tmp)
        try:
            with open(tmp, 'rb') as f:
                sb.storage.from_('papers').upload(fname, f, {'content-type': file.content_type})
            update_data['file_url'] = sb.storage.from_('papers').get_public_url(fname)
            update_data['content_type'] = 'pdf' if ext == '.pdf' else 'doc'
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    elif link_url:
        update_data['file_url'] = link_url
        update_data['content_type'] = 'link'

    if thumbnail and thumbnail.filename:
        ext = os.path.splitext(thumbnail.filename)[1].lower() or '.jpg'
        tname = f"thumb_{uuid_lib.uuid4()}{ext}"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        thumbnail.save(tmp)
        try:
            with open(tmp, 'rb') as f:
                sb.storage.from_('papers').upload(tname, f, {'content-type': thumbnail.content_type})
            update_data['thumbnail_url'] = sb.storage.from_('papers').get_public_url(tname)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    sb.table('papers').update(update_data).eq('id', paper_id).execute()
    return redirect('/admin/papers')


@admin_bp.route('/admin/papers/delete/<paper_id>', methods=['POST'])
@admin_required
def admin_delete_paper(paper_id):
    if sb:
        sb.table('papers').delete().eq('id', paper_id).execute()
    return redirect('/admin/papers')


@admin_bp.route('/admin/papers/publish/<paper_id>', methods=['POST'])
@admin_required
def admin_publish_paper(paper_id):
    if not sb:
        return redirect('/admin/papers')
    result = sb.table('papers').select('*').eq('id', paper_id).execute()
    if not result.data:
        return redirect('/admin/papers')
    paper = result.data[0]
    if paper.get('status') == 'published':
        return redirect('/admin/papers')

    sb.table('papers').update({
        'status': 'published',
        'published_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', paper_id).execute()

    doctors = (sb.table('doctors')
               .select('id, name, email, phone, whatsapp_number, whatsapp_consent, '
                        'email_preference, push_preference, sms_preference')
               .eq('is_active', True).execute()).data or []
    if doctors:
        sb.table('notifications').insert(
            [{'doctor_id': d['id'], 'paper_id': paper_id} for d in doctors]
        ).execute()

        notification_service.trigger_notifications(
            'article_notification', 'multi', doctors, paper)

        if notification_service.is_whatsapp_configured():
            eligible = [d for d in doctors if d.get('whatsapp_consent') and d.get('whatsapp_number')]
            if eligible:
                notification_service.broadcast_whatsapp(eligible, paper)

    return redirect('/admin/papers')


@admin_bp.route('/admin/papers/archive/<paper_id>', methods=['POST'])
@admin_required
def admin_archive_paper(paper_id):
    if sb:
        sb.table('papers').update({'status': 'archived'}).eq('id', paper_id).execute()
    return redirect('/admin/papers')


# ── Doctor management ──────────────────────────────────────────

@admin_bp.route('/admin/doctors/edit/<doctor_id>', methods=['GET'])
@admin_required
def admin_edit_doctor_form(doctor_id):
    doctor = None
    if sb:
        result = sb.table('doctors').select('*').eq('id', doctor_id).execute()
        if result.data:
            doctor = result.data[0]
    if not doctor:
        return redirect('/admin/doctors')
    return render_template('admin_doctor_edit.html', doctor=doctor)


@admin_bp.route('/admin/doctors/edit/<doctor_id>', methods=['POST'])
@admin_required
def admin_edit_doctor(doctor_id):
    name             = request.form.get('name', '').strip()
    phone            = request.form.get('phone', '').strip()
    whatsapp_number  = request.form.get('whatsapp_number', '').strip()
    email            = request.form.get('email', '').strip()
    hospital         = request.form.get('hospital', '').strip()
    specialty        = request.form.get('specialty', '').strip()
    whatsapp_consent = request.form.get('whatsapp_consent') == 'on'
    is_active        = request.form.get('is_active') == 'on'
    if name and sb:
        sb.table('doctors').update({
            'name': name, 'phone': phone, 'whatsapp_number': whatsapp_number,
            'email': email, 'hospital': hospital, 'specialty': specialty,
            'whatsapp_consent': whatsapp_consent, 'is_active': is_active,
        }).eq('id', doctor_id).execute()
    return redirect('/admin/doctors')


@admin_bp.route('/admin/doctors/whatsapp-toggle/<doctor_id>', methods=['POST'])
@admin_required
def admin_toggle_whatsapp(doctor_id):
    if sb:
        doc = (sb.table('doctors').select('whatsapp_consent').eq('id', doctor_id).execute()).data
        if doc:
            sb.table('doctors').update({'whatsapp_consent': not doc[0]['whatsapp_consent']}).eq('id', doctor_id).execute()
    return redirect('/admin/doctors')


@admin_bp.route('/admin/messages', methods=['GET'])
@admin_required
def admin_messages():
    doctors = []
    specialties = []
    if sb:
        doctors = (sb.table('doctors').select('*').eq('is_active', True).order('name').execute()).data or []
        all_docs = (sb.table('doctors').select('specialty').execute()).data or []
        specialties = sorted(set(d.get('specialty', '') for d in all_docs if d.get('specialty')))
    return render_template('admin_messages.html', doctors=doctors, specialties=specialties)


@admin_bp.route('/admin/messages/send', methods=['POST'])
@admin_required
def admin_send_message():
    message_text = request.form.get('message_text', '').strip()
    target       = request.form.get('target', 'all')
    specialty    = request.form.get('specialty', '').strip()
    doctor_ids   = request.form.getlist('doctor_ids')
    channel      = request.form.get('channel', 'multi')

    if not message_text or not sb:
        return redirect('/admin/messages')

    q = sb.table('doctors').select(
        'id, name, email, phone, whatsapp_number, email_preference, push_preference, sms_preference'
    ).eq('is_active', True)
    if target == 'selected' and doctor_ids:
        q = q.in_('id', doctor_ids)
    elif target == 'specialty' and specialty:
        q = q.eq('specialty', specialty)
    doctors = q.execute().data or []

    notification_service.trigger_notifications(
        'manual_message', channel, doctors, None, message_text)
    wa_result = {'total': len(doctors), 'success': 'Queued', 'failed': 0, 'results': []}

    return render_template('admin_message_result.html',
                           message_text=message_text, result=wa_result)


@admin_bp.route('/admin/notifications', methods=['GET'])
@admin_required
def admin_notification_history():
    messages = []
    if sb:
        messages = (sb.table('notification_campaigns')
                    .select('*').order('created_at', desc=True).limit(50)
                    .execute()).data or []
    return render_template('admin_notifications.html', messages=messages)


@admin_bp.route('/admin/notifications/<msg_id>', methods=['GET'])
@admin_required
def admin_notification_detail(msg_id):
    message = None
    delivery_logs = []
    if sb:
        try:
            result = sb.table('notification_campaigns').select('*').eq('id', msg_id).execute()
            if result.data:
                message = result.data[0]
            delivery_logs = (sb.table('notification_delivery_logs')
                             .select('*').eq('campaign_id', msg_id)
                             .order('sent_at', desc=True).execute()).data or []
        except Exception:
            # Fallback to legacy tables
            try:
                result = sb.table('whatsapp_messages').select('*').eq('id', msg_id).execute()
                if result.data:
                    message = result.data[0]
                delivery_logs = (sb.table('whatsapp_delivery_log')
                                 .select('*').eq('message_id', msg_id)
                                 .order('sent_at', desc=True).execute()).data or []
            except Exception:
                pass
    return render_template('admin_notification_detail.html', message=message, delivery_logs=delivery_logs)


def _log_whatsapp_campaign(sb_client, message_type, paper_id, message_body, results):
    try:
        error_details = [r for r in results.get('results', []) if r.get('error')]
        status = 'sent'
        if results['failed'] == results['total']:
            status = 'failed'
        elif results['failed'] > 0:
            status = 'partial'
        msg_result = sb_client.table('whatsapp_messages').insert({
            'message_type': message_type, 'paper_id': paper_id,
            'message_body': message_body[:2000],
            'recipient_count': results['total'], 'success_count': results['success'],
            'fail_count': results['failed'], 'status': status,
            'error_details': error_details[:50], 'sent_by': 'system',
        }).execute()
        if msg_result.data:
            msg_id = msg_result.data[0]['id']
            delivery_rows = [{
                'message_id': msg_id, 'doctor_id': r.get('doctor_id'),
                'whatsapp_number': r.get('whatsapp_number', ''),
                'status': r.get('status', 'failed'), 'error_message': r.get('error'),
            } for r in results.get('results', [])]
            if delivery_rows:
                sb_client.table('whatsapp_delivery_log').insert(delivery_rows).execute()
    except Exception as e:
        current_app.logger.error(f"[WhatsApp Log] Failed: {e}")


@admin_bp.route('/admin/seed-test', methods=['POST'])
@admin_required
def admin_seed_test():
    if not sb:
        return '<p>Supabase not connected.</p><a href="/admin/doctors">Back</a>'
    existing = (sb.table('doctors').select('id').eq('username', 'testdoctor').execute()).data
    if not existing:
        sb.table('doctors').insert({
            'name': 'Dr. Test User', 'username': 'testdoctor',
            'password_hash': generate_password_hash('test1234'),
            'email': '', 'phone': '', 'hospital': 'Demo Hospital',
            'specialty': 'General Medicine', 'is_active': True,
        }).execute()
    paper_count = len((sb.table('papers').select('id').execute()).data or [])
    if paper_count == 0:
        papers_to_insert = [
            {'title': 'RESGABA-NT: Neuropathic Pain Management Guidelines',
             'description': 'Clinical evidence summary for Pregabalin + Nortriptyline combination.',
             'content_type': 'link', 'therapy_area': 'neuropathy',
             'file_url': 'https://pubmed.ncbi.nlm.nih.gov/'},
            {'title': 'Ecoglim MV1 — Glycaemic Control in T2DM',
             'description': 'Phase III data supporting Glimepiride + Metformin + Voglibose.',
             'content_type': 'link', 'therapy_area': 'diabetes',
             'file_url': 'https://pubmed.ncbi.nlm.nih.gov/'},
        ]
        result = sb.table('papers').insert(papers_to_insert).execute()
        if result.data:
            doctors = (sb.table('doctors').select('id').eq('is_active', True).execute()).data or []
            if doctors:
                notifs = [{'doctor_id': d['id'], 'paper_id': p['id']}
                          for d in doctors for p in result.data]
                if notifs:
                    sb.table('notifications').insert(notifs).execute()
    return redirect('/admin/doctors')


@admin_bp.route('/admin/doctors', methods=['GET'])
@admin_required
def admin_doctors():
    doctors = []
    if sb:
        doctors = (sb.table('doctors').select('*').order('created_at', desc=True).execute()).data or []
    return render_template('admin_doctors.html', doctors=doctors)


@admin_bp.route('/admin/doctors/add', methods=['POST'])
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


@admin_bp.route('/admin/doctors/toggle/<doctor_id>', methods=['POST'])
@admin_required
def admin_toggle_doctor(doctor_id):
    if sb:
        doc = (sb.table('doctors').select('is_active').eq('id', doctor_id).execute()).data
        if doc:
            sb.table('doctors').update({'is_active': not doc[0]['is_active']}).eq('id', doctor_id).execute()
    return redirect('/admin/doctors')


@admin_bp.route('/admin/doctors/delete/<doctor_id>', methods=['POST'])
@admin_required
def admin_delete_doctor(doctor_id):
    if sb:
        sb.table('doctors').delete().eq('id', doctor_id).execute()
    return redirect('/admin/doctors')


# ── Debug (now protected) ──────────────────────────────────────

@admin_bp.route('/admin/debug')
@admin_required
def admin_debug():
    from supabase_client import supabase_error as _sb_err
    checks = {}
    checks['supabase_url']  = '✅ Set' if os.getenv('SUPABASE_URL')         else '❌ Missing'
    checks['supabase_key']  = '✅ Set' if os.getenv('SUPABASE_SERVICE_KEY') else '❌ Missing'
    checks['supabase_conn'] = '✅ Connected' if sb else f'❌ {_sb_err or "unknown"}'
    checks['gmail_user']    = '✅ Set' if os.getenv('GMAIL_USER')           else '❌ Missing'
    checks['gmail_pass']    = '✅ Set' if os.getenv('GMAIL_APP_PASSWORD')   else '❌ Missing'
    checks['anthropic_key'] = '✅ Set' if os.getenv('ANTHROPIC_API_KEY')    else '⚠️ Not set'
    if sb:
        try:
            checks['doctors_count'] = str(len((sb.table('doctors').select('id').execute()).data or []))  + ' doctors'
            checks['papers_count']  = str(len((sb.table('papers').select('id').execute()).data or []))   + ' papers'
        except Exception as e:
            checks['db_error'] = f'❌ {e}'
    rows = ''.join(
        f'<tr><td style="padding:10px 16px;font-weight:600;color:#0f1e2d;white-space:nowrap">{k}</td>'
        f'<td style="padding:10px 16px;color:#374151">{v}</td></tr>'
        for k, v in checks.items()
    )
    return f'''<!DOCTYPE html><html><head><title>Debug | Admin</title>
    <style>body{{font-family:sans-serif;padding:40px;background:#f5f7fb}}
    h1{{color:#0f1e2d}}table{{background:#fff;border-radius:12px;border-collapse:collapse;width:100%;max-width:680px;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
    tr{{border-bottom:1px solid #f0f2f5}}td{{font-size:14px}}
    a{{color:#1e6ff1;display:block;margin-top:20px;font-size:14px}}</style></head>
    <body><h1>System Health</h1><table>{rows}</table>
    <a href="/admin/papers">← Back to Admin</a></body></html>'''


# ── AI endpoints ───────────────────────────────────────────────

@admin_bp.route('/doctor/dose-calculator', methods=['POST'])
def dose_calculator():
    data = request.get_json() or {}
    medicine = data.get('medicine', '').strip()
    if not medicine:
        return jsonify({'ok': False, 'reply': 'Please enter a medicine name.'})
    weight     = data.get('weight', '')
    age        = data.get('age', '')
    conditions = [c for c in data.get('conditions', []) if c]
    parts = []
    if weight:     parts.append(f"weight {weight} kg")
    if age:        parts.append(f"age {age} years")
    if conditions: parts.append(f"conditions: {', '.join(conditions)}")
    patient_ctx = '; '.join(parts) if parts else 'no special parameters'
    query = f"Calculate dose for {medicine}. Patient: {patient_ctx}."
    text, err = ai_service.generate_completion(DOSE_CALC_SYSTEM, query)
    if err:
        return jsonify({'ok': False, 'reply': err})
    return jsonify({'ok': True, 'reply': text})


@admin_bp.route('/doctor/drug-interaction', methods=['POST'])
def drug_interaction():
    data = request.get_json() or {}
    drugs = [d.strip() for d in data.get('drugs', []) if d.strip()]
    if len(drugs) < 2:
        return jsonify({'ok': False, 'reply': 'Please enter at least 2 drug names.'})
    query = f"Check all interactions between: {', '.join(drugs)}."
    text, err = ai_service.generate_completion(INTERACTION_SYSTEM, query, max_tokens=1500)
    if err:
        return jsonify({'ok': False, 'reply': err})
    return jsonify({'ok': True, 'reply': text})


# ── Content generator/sender ───────────────────────────────────

@admin_bp.route('/admin/content', methods=['GET'])
@admin_required
def admin_content():
    doctors = []
    if sb:
        doctors = (sb.table('doctors').select('id, name, specialty, email')
                   .eq('is_active', True).order('name').execute()).data or []
    return render_template('admin_content.html', doctors=doctors)


@admin_bp.route('/admin/content/generate', methods=['POST'])
@admin_required
def admin_content_generate():
    data = request.get_json() or {}
    brief = data.get('brief', '').strip()
    audience = data.get('audience', 'all active doctors')
    if not brief:
        return jsonify({'ok': False, 'content': 'Please describe what you want to write.'})
    text, err = ai_service.generate_completion(
        CONTENT_GEN_SYSTEM,
        f'Audience: {audience}.\nBrief: {brief}',
    )
    if err:
        return jsonify({'ok': False, 'content': err})
    return jsonify({'ok': True, 'content': text})


@admin_bp.route('/admin/content/send', methods=['POST'])
@admin_required
def admin_content_send():
    data       = request.get_json() or {}
    subject    = data.get('subject', 'Update from Tunes Pharma').strip()
    content    = data.get('content', '').strip()
    doctor_ids = data.get('doctor_ids', [])
    if not content:
        return jsonify({'ok': False, 'sent': 0, 'message': 'No content to send.'})
    if not sb:
        return jsonify({'ok': False, 'sent': 0, 'message': 'Database not connected.'})
    q = sb.table('doctors').select('id, name, email').eq('is_active', True)
    if doctor_ids:
        q = q.in_('id', doctor_ids)
    doctors = q.execute().data or []
    sent = sum(
        1 for d in doctors
        if d.get('email') and _send_custom_email(d['email'], d['name'], subject, content)
    )
    return jsonify({'ok': True, 'sent': sent, 'total': len(doctors),
                    'message': f'Sent to {sent} of {len(doctors)} doctors.'})


# ── Doctor preferences (legacy route) ─────────────────────────

@admin_bp.route('/api/doctor/preferences', methods=['POST'])
def doctor_preferences():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return jsonify({'error': 'Unauthorized'}), 401
    prefs = request.json
    if not prefs or not sb:
        return jsonify({'error': 'Invalid data'}), 400
    try:
        sb.table('doctors').update({
            'email_preference': prefs.get('email', True),
            'push_preference': prefs.get('push', True),
            'sms_preference': prefs.get('sms', False),
        }).eq('id', doctor_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Preferences update error: {e}")
        return jsonify({'error': 'Update failed'}), 500


# ── Email helper ───────────────────────────────────────────────

def _send_custom_email(doctor_email, doctor_name, subject, content):
    gmail_user = os.getenv('GMAIL_USER', '')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail_user or not gmail_pass or not doctor_email:
        return False
    try:
        from markupsafe import escape
        safe_name = str(escape(doctor_name))
        html_body = content.replace('{{Doctor_Name}}', safe_name).replace('\n', '<br>')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"Tunes Pharma <{gmail_user}>"
        msg['To']      = doctor_email
        html = f"""
        <div style="font-family:'Poppins',Arial,sans-serif;max-width:580px;margin:0 auto;
             background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e8ecf0">
          <div style="background:linear-gradient(135deg,#0a1628,#1e3a52);padding:28px 36px;text-align:center">
            <p style="color:rgba(255,255,255,.5);font-size:12px;letter-spacing:.1em;
               text-transform:uppercase;margin:0">Tunes Pharma</p>
          </div>
          <div style="padding:36px;color:#374151;font-size:14px;line-height:1.8">{html_body}</div>
          <div style="background:#f8fafc;padding:16px 36px;border-top:1px solid #e8ecf0;text-align:center">
            <p style="color:#94a3b8;font-size:11px;margin:0">Tunes Pharma · Vijayawada, AP</p>
          </div>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, doctor_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error(f"[Email] Failed: {e}")
        return False
