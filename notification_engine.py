import os
import smtplib
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor
from pywebpush import webpush, WebPushException

# Optionally support Twilio
try:
    from twilio.rest import Client
except ImportError:
    Client = None

# Initialize background thread pool
executor = ThreadPoolExecutor(max_workers=5)
logger = logging.getLogger(__name__)

def send_email_notification(doctor_email, doctor_name, paper_title, paper_description, paper_url, therapy_area):
    """Send a paper notification email to a single doctor via Gmail SMTP."""
    gmail_user = os.getenv('GMAIL_USER', '')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail_user or not gmail_pass or not doctor_email:
        logger.warning(f"[Email] Missing credentials or email for {doctor_email}")
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
            <p style="color:rgba(255,255,255,.5);font-size:12px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 8px">Tunes Pharma</p>
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
          </div>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, doctor_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"[Email] Failed to send to {doctor_email}: {e}")
        return False

def send_push_notification(subscription_info, payload):
    """Send a Web Push notification to a specific subscription."""
    try:
        vapid_private = os.getenv('VAPID_PRIVATE_KEY')
        vapid_claim = os.getenv('VAPID_CLAIM_EMAIL')
        if not vapid_private or not vapid_claim:
            logger.warning("[Push] VAPID keys not configured.")
            return False
            
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims={"sub": f"mailto:{vapid_claim}"}
        )
        return True
    except WebPushException as ex:
        logger.error(f"[Push] Error sending push: {repr(ex)}")
        if ex.response and ex.response.status_code == 410:
            # Indicates subscription has expired/unsubscribed
            return 'expired'
        return False
    except Exception as e:
        logger.error(f"[Push] Unexpected error: {e}")
        return False

def send_sms_notification(phone_number, text_message):
    """Send an SMS notification using Twilio or a mock adapter."""
    if not phone_number:
        return False
        
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_auth = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_from = os.getenv('TWILIO_PHONE_NUMBER')
    
    if twilio_sid and twilio_auth and twilio_from and Client:
        try:
            client = Client(twilio_sid, twilio_auth)
            message = client.messages.create(
                body=text_message,
                from_=twilio_from,
                to=phone_number
            )
            return True
        except Exception as e:
            logger.error(f"[SMS] Twilio error for {phone_number}: {e}")
            return False
    else:
        # Mock SMS integration
        logger.info(f"[SMS MOCK] Sending SMS to {phone_number}: {text_message}")
        return True

def _log_delivery(sb, campaign_id, doctor_id, channel, contact_info, status, error_message=None):
    if not sb: return
    try:
        sb.table('notification_delivery_logs').insert({
            'campaign_id': campaign_id,
            'doctor_id': doctor_id,
            'channel': channel,
            'contact_info': contact_info,
            'status': status,
            'error_message': error_message
        }).execute()
    except Exception as e:
        logger.error(f"[Log] Failed to insert delivery log: {e}")

def process_channel_notifications(sb, campaign_id, doctors, channel_type, article_data, manual_msg=None):
    """Process notifications for a specific channel asynchronously."""
    success_count = 0
    fail_count = 0
    
    for doctor in doctors:
        doc_id = doctor.get('id')
        status = 'failed'
        error = None
        
        if channel_type == 'email' and doctor.get('email_preference', True):
            email = doctor.get('email')
            if email:
                if manual_msg:
                    sent = send_email_notification(email, doctor.get('name'), "Admin Message", manual_msg, "", "general")
                else:
                    sent = send_email_notification(
                        email, doctor.get('name'), article_data['title'],
                        article_data.get('description', ''), article_data['url'],
                        article_data.get('therapy_area', 'general')
                    )
                status = 'delivered' if sent else 'failed'
                _log_delivery(sb, campaign_id, doc_id, 'email', email, status)
                if sent: success_count += 1
                else: fail_count += 1
                
        elif channel_type == 'sms' and doctor.get('sms_preference', False):
            phone = doctor.get('phone')
            if phone:
                msg = manual_msg or f"New Article: {article_data['title']}. Visit Tunes Pharma to read."
                sent = send_sms_notification(phone, msg)
                status = 'delivered' if sent else 'failed'
                _log_delivery(sb, campaign_id, doc_id, 'sms', phone, status)
                if sent: success_count += 1
                else: fail_count += 1
                
        elif channel_type == 'push' and doctor.get('push_preference', True):
            # Fetch subscriptions for this doctor
            try:
                subs_res = sb.table('push_subscriptions').select('*').eq('doctor_id', doc_id).execute()
                subs = subs_res.data or []
            except Exception:
                subs = []
                
            if subs:
                payload = {
                    "title": "New Admin Message" if manual_msg else "New Academic Insight Published",
                    "body": manual_msg or f"{article_data['title']} is now available.",
                    "url": "/doctor-portal#research" if not manual_msg else "/doctor-portal"
                }
                for sub in subs:
                    sub_json = sub.get('subscription_json')
                    res = send_push_notification(sub_json, payload)
                    if res == 'expired':
                        # Clean up expired subscriptions
                        sb.table('push_subscriptions').delete().eq('id', sub['id']).execute()
                        fail_count += 1
                    elif res:
                        success_count += 1
                        _log_delivery(sb, campaign_id, doc_id, 'push', 'web_push', 'delivered')
                    else:
                        fail_count += 1
                        _log_delivery(sb, campaign_id, doc_id, 'push', 'web_push', 'failed')
    
    # Update campaign counts
    if sb:
        try:
            current_res = sb.table('notification_campaigns').select('success_count, fail_count').eq('id', campaign_id).execute()
            if current_res.data:
                curr = current_res.data[0]
                new_success = curr['success_count'] + success_count
                new_fail = curr['fail_count'] + fail_count
                new_status = 'sent' if new_fail == 0 else ('partial' if new_success > 0 else 'failed')
                sb.table('notification_campaigns').update({
                    'success_count': new_success,
                    'fail_count': new_fail,
                    'status': new_status
                }).eq('id', campaign_id).execute()
        except Exception as e:
            logger.error(f"[Log] Failed to update campaign log: {e}")

def trigger_notifications(sb, message_type, channel, target_doctors, article_data=None, manual_message=None):
    """
    Queue notifications to be sent via the specified channel.
    message_type: 'article_notification' or 'manual_message'
    channel: 'email', 'push', 'sms', 'multi'
    """
    if not sb: return
    
    # Create Campaign Log
    try:
        campaign = sb.table('notification_campaigns').insert({
            'message_type': message_type,
            'channel': channel,
            'paper_id': article_data['id'] if article_data else None,
            'message_body': manual_message or (article_data.get('title') if article_data else ''),
            'recipient_count': len(target_doctors),
            'status': 'pending'
        }).execute()
        campaign_id = campaign.data[0]['id']
    except Exception as e:
        logger.error(f"[Engine] Failed to create campaign: {e}")
        return

    channels_to_process = ['email', 'push', 'sms'] if channel == 'multi' else [channel]
    
    for ch in channels_to_process:
        executor.submit(
            process_channel_notifications, 
            sb, campaign_id, target_doctors, ch, article_data, manual_message
        )
