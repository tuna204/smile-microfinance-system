"""
Notifications fired when staff confirms a bank transfer via
/admin/record-payment. Email uses Flask-Mail (any SMTP provider —
SendGrid/Mailgun recommended for production deliverability). SMS uses
Termii, which is built for Nigerian numbers. Contact-form messages use
Resend instead, since it's more reliable for that path.

send_notifications_async() is what routes should call for PAYMENT
notifications — it runs send_payment_email/send_payment_sms in a
background thread, so a slow or broken mail/SMS provider can never hang
or crash the request the admin is waiting on. Failures are logged, not
raised — by the time this runs, the money has already been credited, so
a failed notification is a followup problem, not a reason to fail the
whole action.
"""
import threading
import requests
from flask import current_app
from flask_mail import Message
from extensions import mail
from html import escape
import resend


def send_payment_email(member, amount, new_balance):
    msg = Message(
        subject="Payment received — Smile Cooperative",
        recipients=[member.email],
        body=(
            f"Hello {member.full_name},\n\n"
            f"We've received your payment of NGN {amount:,.2f}. "
            f"Your savings balance is now NGN {new_balance:,.2f}.\n\n"
            f"Your Smile remains Our Joy."
        ),
    )
    mail.send(msg)


def send_payment_sms(member, amount):
    api_key = current_app.config.get("TERMII_API_KEY")
    if not api_key:
        current_app.logger.warning("TERMII_API_KEY not set — skipping SMS")
        return None

    resp = requests.post(
        "https://api.ng.termii.com/api/sms/send",
        json={
            "to": member.phone,
            "from": current_app.config.get("TERMII_SENDER_ID", "Smile"),
            "sms": f"Smile: Payment of NGN {amount:,.2f} received. Thank you!",
            "type": "plain",
            "channel": "generic",
            "api_key": api_key,
        },
        timeout=15,
    )
    return resp.json()


def send_contact_message(full_name, email, message):
    """Send a contact-form submission to the company inbox using Resend."""

    resend.api_key = current_app.config["RESEND_API_KEY"]

    safe_name = escape(full_name)
    safe_email = escape(email)
    safe_message = escape(message).replace("\n", "<br>")

    params = {
        "from": "Smile <info@mysmile.ng>",
        "to": [current_app.config["CONTACT_RECIPIENT"]],
        "reply_to": email,
        "subject": f"New contact form message from {full_name}",
        "html": f"""
            <h2>New Contact Form Message</h2>
            <p><strong>Name:</strong> {safe_name}</p>
            <p><strong>Email:</strong> {safe_email}</p>
            <h3>Message</h3>
            <p>{safe_message}</p>
        """,
    }

    return resend.Emails.send(params)


def _send_notifications_background(app, member_id, amount):
    """Runs in a background thread — needs its own app context since
    Flask's current_app/request context doesn't carry over to a new
    thread automatically."""
    with app.app_context():
        from models import Member
        member = Member.query.get(member_id)
        if not member:
            return

        try:
            send_payment_email(member, amount, member.savings_account.balance)
        except Exception as e:
            app.logger.error(f"Background email notification failed for member {member_id}: {e}")

        try:
            send_payment_sms(member, amount)
        except Exception as e:
            app.logger.error(f"Background SMS notification failed for member {member_id}: {e}")


def send_notifications_async(member, amount):
    """Call this from routes instead of send_payment_email/send_payment_sms
    directly, for PAYMENT confirmations. Fires both in a background
    thread and returns immediately — the admin's request never waits on
    email/SMS at all. (Contact-form messages still go through
    send_contact_message() directly, unchanged — that path isn't the one
    that was crashing.)"""
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_send_notifications_background,
        args=(app, member.id, amount),
        daemon=True,
    )
    thread.start()
