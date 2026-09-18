"""
The ledger service is the ONLY place in the codebase allowed to change a
member's balance. Never edit SavingsAccount.balance directly anywhere
else — always go through record_deposit() so every change is logged.
"""
from datetime import datetime
from decimal import Decimal
from extensions import db
from models import Transaction, SavingsAccount, Member

REVIEW_THRESHOLD_NGN = Decimal("500000")
REGISTRATION_FEE_NGN = Decimal("5000")
REFERRAL_BONUS_NGN = Decimal("1000")


def record_deposit(member, amount, source="manual", gateway_reference=None, narration=None):
    """Create a transaction for a deposit and reflect it in the member's
    savings balance. Returns the Transaction row."""
    amount = Decimal(str(amount))

    txn = Transaction(
        member_id=member.id,
        type="deposit",
        amount=amount,
        status="reflected",
        source=source,
        gateway_reference=gateway_reference,
        narration=narration,
        reflected_at=datetime.utcnow(),
    )

    account = member.savings_account
    if account is None:
        account = SavingsAccount(member_id=member.id, balance=0)
        db.session.add(account)

    account.balance = (account.balance or Decimal("0")) + amount
    account.updated_at = datetime.utcnow()

    db.session.add(txn)
    db.session.commit()
    return txn


def create_deposit_request(member, amount, narration=None):
    """A member saying 'I intend to save this amount' — creates a PENDING
    transaction for visibility only. Does NOT touch the balance."""
    amount = Decimal(str(amount))
    txn = Transaction(
        member_id=member.id,
        type="deposit",
        amount=amount,
        status="pending",
        source="member_request",
        narration=narration or "Member requested to save",
    )
    db.session.add(txn)
    db.session.commit()
    return txn


def confirm_registration_fee(member, admin_member=None):
    """Confirms the one-time ₦5,000 registration fee and activates the
    member. Does NOT touch the savings balance — this fee isn't the
    member's money.

    If this member was referred by someone (member.referred_by_id), this
    is also the moment a ₦1,000 referral bonus becomes owed to that
    referrer — created here as a separate pending payout, since we only
    want to reward referrals of real, paying members, not bare signups.
    """
    if member.registration_fee_paid:
        return None  # already activated — avoid a duplicate transaction

    txn = Transaction(
        member_id=member.id,
        type="registration_fee",
        amount=REGISTRATION_FEE_NGN,
        status="reflected",
        source="admin_action",
        narration=(
            f"Registration fee confirmed by {admin_member.full_name}"
            if admin_member else "Registration fee confirmed"
        ),
        reflected_at=datetime.utcnow(),
    )
    db.session.add(txn)

    member.registration_fee_paid = True
    member.is_active_member = True

    # Referral bonus — only fires once, right here, only for real activations.
    if member.referred_by_id:
        referrer = Member.query.get(member.referred_by_id)
        if referrer:
            bonus_txn = Transaction(
                member_id=referrer.id,
                type="referral_bonus",
                amount=REFERRAL_BONUS_NGN,
                status="pending_payout",
                source="system",
                narration=f"Referral bonus for referring {member.full_name} ({member.membership_no})",
            )
            db.session.add(bonus_txn)

    db.session.commit()
    return txn


def mark_referral_paid(txn, admin_member):
    """Admin confirms they've manually sent the ₦1,000 to the referrer's
    own bank account (member.payout_account_number etc.)."""
    txn.status = "paid_out"
    txn.reviewed_at = datetime.utcnow()
    txn.reviewed_by_id = admin_member.id
    db.session.commit()
    return txn


def needs_review(txn):
    """Whether this transaction should be surfaced in the admin
    'awaiting review' queue."""
    return txn.status == "reflected" and txn.type == "deposit" and txn.amount >= REVIEW_THRESHOLD_NGN


def mark_reviewed(txn, admin_member):
    txn.status = "reviewed"
    txn.reviewed_at = datetime.utcnow()
    txn.reviewed_by_id = admin_member.id
    db.session.commit()
    return txn


def recompute_balance(member):
    """Rebuild a member's balance from the transaction history — audit
    tool only, should never be needed if record_deposit() is the only
    write path. Deliberately excludes registration_fee and
    referral_bonus types, since neither is savings."""
    total = Decimal("0")
    for txn in member.transactions.filter(
        Transaction.status.in_(["reflected", "reviewed"]),
        Transaction.type.in_(["deposit", "loan_disbursement", "investment_payout", "dividend"]),
    ):
        if txn.type in ("deposit", "loan_disbursement", "investment_payout", "dividend"):
            total += txn.amount
        elif txn.type in ("withdrawal", "loan_repayment", "investment_deposit"):
            total -= txn.amount

    account = member.savings_account
    if account:
        account.balance = total
        db.session.commit()
    return total
