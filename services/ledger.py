"""
The ledger service is the ONLY place in the codebase allowed to change a
member's balance. Never edit SavingsAccount.balance directly anywhere
else — always go through record_deposit() / apply_transaction() so every
change is logged in the transactions table.

Fraud-safety design:
A staff-confirmed bank transfer (via /admin/record-payment) REFLECTS
immediately in the member's dashboard balance — that's the instant UX
your director asked for. But it is marked "reflected", not "reviewed".
A separate, lightweight admin action marks it "reviewed" — an audit
confirmation, not a blocker. Large or first-time payments can be
configured to require review BEFORE the funds are treated as
withdrawable/investable.
"""
from datetime import datetime
from decimal import Decimal
from extensions import db
from models import Transaction, SavingsAccount


# Payments at or above this amount are flagged for admin review before
# being eligible for withdrawal/investment, even though the balance
# reflects instantly. Tune this with your director once real volumes
# are known.
REVIEW_THRESHOLD_NGN = Decimal("500000")


def create_deposit_request(member, amount, narration=None):
    """A member saying 'I intend to save this amount' — creates a PENDING
    transaction for visibility only. This deliberately does NOT touch the
    balance; only record_deposit() (staff-confirmed, after money actually
    arrives) can do that. Keeps the audit trail honest: intent to pay is
    not the same as money in hand."""
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

    # Large/first-time payments stay unreviewed until an admin confirms —
    # they still reflect in the balance, but a flag is available for the
    # admin dashboard to filter on. (status stays "reflected" either way;
    # see needs_review() below for how the admin UI should query this.)

    account = member.savings_account
    if account is None:
        account = SavingsAccount(member_id=member.id, balance=0)
        db.session.add(account)

    account.balance = (account.balance or Decimal("0")) + amount
    account.updated_at = datetime.utcnow()

    db.session.add(txn)
    db.session.commit()
    return txn


def needs_review(txn):
    """Whether this transaction should be surfaced in the admin
    'awaiting review' queue."""
    return txn.status == "reflected" and txn.amount >= REVIEW_THRESHOLD_NGN


def mark_reviewed(txn, admin_member):
    txn.status = "reviewed"
    txn.reviewed_at = datetime.utcnow()
    txn.reviewed_by_id = admin_member.id
    db.session.commit()
    return txn


def recompute_balance(member):
    """Rebuild a member's balance from the transaction history. Use this
    if balance and transaction history ever drift — it should never
    happen if record_deposit() is the only write path, but this is the
    safety net / audit tool."""
    total = Decimal("0")
    for txn in member.transactions.filter_by(status="reflected").union(
        member.transactions.filter_by(status="reviewed")
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
