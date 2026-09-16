"""
Notifications fired when staff confirms a bank transfer via
/admin/record-payment. Email uses Flask-Mail (any SMTP provider —
SendGrid/Mailgun recommended for production deliverability). SMS uses
Termii, which is built for Nigerian numbers.
"""
import requests
from flask import current_app
from flask_mail import Message
from extensions import mail


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


# ============================================================
# ADD THIS FUNCTION to services/notify.py — don't remove
# anything already there (send_payment_email, send_payment_sms).
# ============================================================

def send_contact_message(full_name, email, message):
    """Sends a contact-form submission to the company inbox. Uses the
    same Flask-Mail setup as payment notifications."""
    msg = Message(
        subject=f"New contact form message from {full_name}",
        recipients=[current_app.config.get("MAIL_DEFAULT_SENDER")],
        reply_to=email,
        body=f"From: {full_name} <{email}>\n\n{message}",
    )
    mail.send(msg)
