import os
import uuid
import random
import string
from datetime import datetime, date

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Member, SavingsAccount

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2MB — matches the frontend check in main.js


def _generate_membership_no():
    """SM-2026-XXXXX format. Retries on the rare collision."""
    while True:
        candidate = f"SM-{date.today().year}-{''.join(random.choices(string.digits, k=5))}"
        if not Member.query.filter_by(membership_no=candidate).first():
            return candidate


def _save_passport_photo(file_storage, membership_no):
    """Validates and saves the uploaded passport photo. Returns the
    public URL path to store on the member, or None if no valid file
    was uploaded.

    IMPORTANT — Railway's filesystem is ephemeral (wiped on every
    redeploy), same issue as the SQLite decision earlier. This local-disk
    approach is fine for development, but before going live, swap this
    for an external storage service (Cloudinary has a generous free
    tier and is simple to wire in) so photos survive deployments.
    """
    if not file_storage or file_storage.filename == "":
        return None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        flash("Passport photo must be a JPG or PNG file.", "error")
        return None

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_PHOTO_BYTES:
        flash("Passport photo must be under 2MB.", "error")
        return None

    upload_dir = os.path.join(current_app.static_folder, "uploads", "passports")
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(f"{membership_no}-{uuid.uuid4().hex[:8]}.{ext}")
    file_storage.save(os.path.join(upload_dir, filename))

    return f"/static/uploads/passports/{filename}"


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()

        if Member.query.filter((Member.email == email) | (Member.phone == phone)).first():
            flash("An account with that email or phone already exists.", "error")
            return redirect(url_for("public.membership") + "#register")

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("public.membership") + "#register")

        dob_raw = request.form.get("date_of_birth", "").strip()
        dob = None
        if dob_raw:
            try:
                dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
            except ValueError:
                pass  # leave as None rather than fail registration over a bad date

        membership_no = _generate_membership_no()
        photo_url = _save_passport_photo(request.files.get("passport_photo"), membership_no)

        member = Member(
            membership_no=membership_no,
            full_name=request.form.get("full_name", "").strip(),
            gender=request.form.get("gender"),
            date_of_birth=dob,
            phone=phone,
            email=email,
            residential_address=request.form.get("residential_address"),
            occupation=request.form.get("occupation"),
            next_of_kin=request.form.get("next_of_kin"),
            savings_frequency=request.form.get("savings_frequency"),
            remarks=request.form.get("remarks"),
            passport_photo_url=photo_url,
            date_joined=datetime.utcnow(),
        )
        member.set_password(password)

        db.session.add(member)
        db.session.flush()  # get member.id before creating the savings account

        db.session.add(SavingsAccount(member_id=member.id, balance=0))
        db.session.commit()

        # NOTE: if a payment gateway is ever added back, virtual-account
        # creation would happen here on registration.

        flash(
            f"Account created! Your membership number is {member.membership_no}. "
            f"Log in below to access your dashboard.",
            "success",
        )
        return redirect(url_for("public.membership") + "#login")

    return redirect(url_for("public.membership") + "#register")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        member = Member.query.filter(
            (Member.email == identifier) | (Member.membership_no == identifier)
        ).first()

        if member and member.check_password(password):
            login_user(member, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.home"))

        flash("Incorrect login details.", "error")

    return redirect(url_for("public.membership") + "#login")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public.membership") + "#login")
