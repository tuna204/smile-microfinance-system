from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from services.notify import send_contact_message

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")


@public_bp.route("/about")
def about():
    return render_template("public/about.html")


@public_bp.route("/products")
def products():
    return render_template("public/products.html")


@public_bp.route("/how-it-works")
def how_it_works():
    return render_template("public/how-it-works.html")


@public_bp.route("/refer-and-earn")
def refer_and_earn():
    return render_template("public/refer-earn.html")


@public_bp.route("/faq")
def faq():
    return render_template("public/faq.html")


@public_bp.route("/membership")
def membership():
    return render_template("public/membership.html")


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not full_name or not email or not message:
            flash("Please fill in every field.", "error")
            return redirect(url_for("public.contact"))

        try:
            send_contact_message(full_name, email, message)
            flash("Thanks your message has been sent. We'll get back to you soon.", "success")
        except Exception as e:
            current_app.logger.error(f"Contact form email failed: {e}")
            flash("Sorry, something went wrong sending your message. Please try WhatsApp or email us directly.", "error")

        return redirect(url_for("public.contact"))

    return render_template("public/contact.html")
