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
