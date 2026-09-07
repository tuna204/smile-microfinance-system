from flask import Blueprint, render_template

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


@public_bp.route("/faq")
def faq():
    return render_template("public/faq.html")


@public_bp.route("/membership")
def membership():
    return render_template("public/membership.html")


@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html")
