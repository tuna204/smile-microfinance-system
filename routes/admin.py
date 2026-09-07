from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from models import Member
from services.ledger import needs_review, mark_reviewed, record_deposit
from services.notify import send_payment_email, send_payment_sms

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@login_required
@admin_required
def home():
    from models import Transaction
    members_count = Member.query.filter_by(role="member").count()
    pending_review = [
        txn for txn in Transaction.query.filter_by(status="reflected").all()
        if needs_review(txn)
    ]
    return render_template(
        "admin/home.html",
        members_count=members_count,
        pending_review=pending_review,
    )


@admin_bp.route("/record-payment", methods=["GET", "POST"])
@login_required
@admin_required
def record_payment():
    """The core of the fee-free reconciliation flow: a member transfers
    directly to the company bank account using their membership number
    as the transfer narration. Staff sees the bank alert (SMS/app) like
    normal, and confirms it here. From that one click, the balance
    updates and email + SMS notifications fire automatically — the only
    manual step is this glance-and-confirm, not full bank detection."""

    if request.method == "POST":
        membership_no = request.form.get("membership_no", "").strip().upper()
        amount = request.form.get("amount", "").strip()
        narration = request.form.get("narration", "").strip()

        member = Member.query.filter_by(membership_no=membership_no).first()
        if not member:
            flash(f"No member found with membership number {membership_no}.", "error")
            return redirect(url_for("admin.record_payment"))

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid amount greater than zero.", "error")
            return redirect(url_for("admin.record_payment"))

        txn = record_deposit(
            member,
            amount=amount_val,
            source="admin_action",
            narration=narration or f"Bank transfer confirmed by {current_user.full_name}",
        )

        try:
            send_payment_email(member, amount_val, member.savings_account.balance)
        except Exception as e:
            flash(f"Payment recorded, but email notification failed: {e}", "error")

        try:
            send_payment_sms(member, amount_val)
        except Exception as e:
            flash(f"Payment recorded, but SMS notification failed: {e}", "error")

        flash(
            f"₦{amount_val:,.2f} recorded for {member.full_name} ({member.membership_no}). "
            f"New balance: ₦{member.savings_account.balance:,.2f}",
            "success",
        )
        return redirect(url_for("admin.record_payment"))

    return render_template("admin/record_payment.html")


@admin_bp.route("/review/<int:txn_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_review(txn_id):
    from models import Transaction
    txn = Transaction.query.get_or_404(txn_id)
    mark_reviewed(txn, current_user)
    flash(f"Transaction #{txn.id} marked as reviewed.", "success")
    return redirect(url_for("admin.home"))
