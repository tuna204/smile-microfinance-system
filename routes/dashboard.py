from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from services.ledger import create_deposit_request, REGISTRATION_FEE_NGN

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def home():
    member = current_user
    account = member.savings_account

    from models import Transaction, Member
    recent_transactions = (
        member.transactions.order_by(Transaction.created_at.desc()).limit(10).all()
    )
    pending_requests = (
        member.transactions.filter_by(status="pending", source="member_request")
        .order_by(Transaction.created_at.desc()).all()
    )

    referral_link = url_for("public.membership", ref=member.membership_no, _external=True)
    referral_count = Member.query.filter_by(referred_by_id=member.id).count()

    return render_template(
        "dashboard/home.html",
        member=member,
        balance=account.balance if account else 0,
        loans=member.loans.all(),
        investments=member.investments.all(),
        transactions=recent_transactions,
        pending_requests=pending_requests,
        registration_fee_amount=REGISTRATION_FEE_NGN,
        referral_link=referral_link,
        referral_count=referral_count,
    )


@dashboard_bp.route("/request-deposit", methods=["POST"])
@login_required
def request_deposit():
    if not current_user.registration_fee_paid:
        flash("Activate your membership first — pay the one-time ₦5,000 registration fee shown on your dashboard.", "error")
        return redirect(url_for("dashboard.home"))

    amount = request.form.get("amount", "").strip()

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid amount greater than zero.", "error")
        return redirect(url_for("dashboard.home"))

    create_deposit_request(current_user, amount_val)
    flash(
        f"Request created for ₦{amount_val:,.2f}. Transfer to the company account below "
        f"using your membership number as the description — your balance updates once staff confirm it.",
        "success",
    )
    return redirect(url_for("dashboard.home"))
