from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from models import Member
from services.ledger import (
    needs_review, mark_reviewed, record_deposit, confirm_registration_fee,
    mark_referral_paid, approve_deposit_request,
)
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
    pending_referrals_count = Transaction.query.filter_by(
        type="referral_bonus", status="pending_payout"
    ).count()
    pending_deposits_count = Transaction.query.filter_by(
        type="deposit", status="pending", source="member_request"
    ).count()
    return render_template(
        "admin/home.html",
        members_count=members_count,
        pending_review=pending_review,
        pending_referrals_count=pending_referrals_count,
        pending_deposits_count=pending_deposits_count,
    )


@admin_bp.route("/pending-deposits")
@login_required
@admin_required
def pending_deposits():
    """The queue your director asked for: every member's own 'Add Money'
    request, waiting for staff to approve once the transfer actually
    arrives. Approving here flips the SAME row from pending to approved
    (see services/ledger.py::approve_deposit_request) — the member sees
    that exact status change on their own dashboard."""
    from models import Transaction
    pending = (
        Transaction.query.filter_by(type="deposit", status="pending", source="member_request")
        .order_by(Transaction.created_at.asc()).all()
    )
    rows = [(txn, Member.query.get(txn.member_id)) for txn in pending]
    return render_template("admin/pending_deposits.html", rows=rows)


@admin_bp.route("/pending-deposits/<int:txn_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_pending_deposit(txn_id):
    from models import Transaction
    txn = Transaction.query.get_or_404(txn_id)

    result = approve_deposit_request(txn, admin_member=current_user)
    if result is None:
        flash("This request was already handled.", "error")
        return redirect(url_for("admin.pending_deposits"))

    member = Member.query.get(txn.member_id)
    try:
        send_payment_email(member, txn.amount, member.savings_account.balance)
    except Exception as e:
        flash(f"Approved, but email notification failed: {e}", "error")
    try:
        send_payment_sms(member, txn.amount)
    except Exception as e:
        flash(f"Approved, but SMS notification failed: {e}", "error")

    flash(f"₦{txn.amount:,.2f} approved for {member.full_name} ({member.membership_no}).", "success")
    return redirect(url_for("admin.pending_deposits"))


@admin_bp.route("/record-payment", methods=["GET", "POST"])
@login_required
@admin_required
def record_payment():
    """For payments staff learns about WITHOUT a prior member request
    (e.g. someone transfers without generating a request first). If the
    member already has a matching pending request, use the Pending
    Deposits queue instead — this always creates a fresh transaction."""
    if request.method == "POST":
        membership_no = request.form.get("membership_no", "").strip().upper()
        payment_type = request.form.get("payment_type", "savings")

        member = Member.query.filter_by(membership_no=membership_no).first()
        if not member:
            flash(f"No member found with membership number {membership_no}.", "error")
            return redirect(url_for("admin.record_payment"))

        if payment_type == "registration_fee":
            if member.registration_fee_paid:
                flash(f"{member.full_name} ({member.membership_no}) is already activated.", "error")
                return redirect(url_for("admin.record_payment"))

            confirm_registration_fee(member, admin_member=current_user)
            flash(
                f"Registration fee confirmed for {member.full_name} ({member.membership_no}). "
                f"Membership is now active."
                + (" A referral bonus is now pending payout for their referrer." if member.referred_by_id else ""),
                "success",
            )
            return redirect(url_for("admin.record_payment"))

        amount = request.form.get("amount", "").strip()
        narration = request.form.get("narration", "").strip()

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


@admin_bp.route("/members")
@login_required
@admin_required
def members():
    """Directory of every member, including the payout bank details they
    submitted at registration — for loan disbursement, dividends, or
    just looking someone up. Optional search by name/membership number/email."""
    q = request.args.get("q", "").strip()
    query = Member.query.filter_by(role="member")
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Member.full_name.ilike(like)) |
            (Member.membership_no.ilike(like)) |
            (Member.email.ilike(like))
        )
    all_members = query.order_by(Member.created_at.desc()).all()
    return render_template("admin/members.html", members=all_members, q=q)


@admin_bp.route("/promote-admin", methods=["GET", "POST"])
@login_required
@admin_required
def promote_admin():
    """The permanent, safe replacement for the one-time secret-URL
    bootstrap trick — only someone ALREADY an admin can reach this page
    at all, so there's no public exposure risk."""
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        member = Member.query.filter(
            (Member.email == identifier) | (Member.membership_no == identifier.upper())
        ).first()

        if not member:
            flash(f"No member found matching {identifier}.", "error")
            return redirect(url_for("admin.promote_admin"))

        if member.role == "admin":
            flash(f"{member.full_name} is already an admin.", "error")
            return redirect(url_for("admin.promote_admin"))

        member.role = "admin"
        from extensions import db
        db.session.commit()
        flash(f"{member.full_name} ({member.email}) is now an admin.", "success")
        return redirect(url_for("admin.promote_admin"))

    return render_template("admin/promote_admin.html")


@admin_bp.route("/referral-payouts")
@login_required
@admin_required
def referral_payouts():
    from models import Transaction
    pending = (
        Transaction.query.filter_by(type="referral_bonus", status="pending_payout")
        .order_by(Transaction.created_at.asc()).all()
    )
    rows = [(txn, Member.query.get(txn.member_id)) for txn in pending]
    return render_template("admin/referral_payouts.html", rows=rows)


@admin_bp.route("/referral-payouts/<int:txn_id>/mark-paid", methods=["POST"])
@login_required
@admin_required
def mark_referral_payout_paid(txn_id):
    from models import Transaction
    txn = Transaction.query.get_or_404(txn_id)
    if txn.type != "referral_bonus" or txn.status != "pending_payout":
        flash("This isn't a pending referral payout.", "error")
        return redirect(url_for("admin.referral_payouts"))

    mark_referral_paid(txn, current_user)
    flash(f"Referral bonus #{txn.id} marked as paid out.", "success")
    return redirect(url_for("admin.referral_payouts"))


@admin_bp.route("/review/<int:txn_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_review(txn_id):
    from models import Transaction
    txn = Transaction.query.get_or_404(txn_id)
    mark_reviewed(txn, current_user)
    flash(f"Transaction #{txn.id} marked as reviewed.", "success")
    return redirect(url_for("admin.home"))



# ============================================================
# TEMPORARY — paste this into routes/admin.py, anywhere below
# the existing routes. DELETE IT once you've used it once.
# This is ONLY needed for your very first admin ever — every
# admin after this one gets added through /admin/promote-admin.
# ============================================================

@admin_bp.route("/bootstrap-first-admin/CHANGE-THIS-TO-SOMETHING-SECRET/<email>")
def bootstrap_first_admin(email):
    member = Member.query.filter_by(email=email.strip().lower()).first()

    if not member:
        return f"No member found with email {email}. Register that account first."

    if member.role == "admin":
        return f"{member.full_name} is already an admin."

    member.role = "admin"
    from extensions import db
    db.session.commit()
    return f"Done! {member.full_name} ({email}) is now an admin. DELETE THIS ROUTE NOW and push again."
