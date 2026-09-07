from datetime import datetime
from extensions import db


class Transaction(db.Model):
    """The single source of truth for money movement. Every deposit,
    loan disbursement, investment payout, or dividend is ONE ROW here.
    Account balances are recalculated FROM this table — never the other
    way around. This is what makes the system auditable: if a member
    disputes a balance, this table is the paper trail.
    """

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)

    type = db.Column(db.String(30), nullable=False)
    # deposit / loan_disbursement / loan_repayment / investment_deposit /
    # investment_payout / dividend / withdrawal

    amount = db.Column(db.Numeric(14, 2), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pending")
    # pending -> reflected (balance updated) -> reviewed (admin confirmed, audit only)
    # A transaction can be "reflected" (member sees it, balance updated)
    # WITHOUT being "reviewed" yet — see services/ledger.py for why this
    # split exists (fraud/AML safety net).

    source = db.Column(db.String(30), nullable=False, default="manual")
    # manual / admin_action / (future: a payment gateway if one gets added)

    gateway_reference = db.Column(db.String(120), unique=True, index=True)
    narration = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reflected_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("members.id"))


class DividendPayout(db.Model):
    """A dividend declared for a member — usually created in a batch by
    an admin, then converted into a Transaction when paid."""

    __tablename__ = "dividend_payouts"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)

    amount = db.Column(db.Numeric(14, 2), nullable=False)
    period_label = db.Column(db.String(50))  # e.g. "2026 Q3"
    status = db.Column(db.String(20), default="declared")  # declared / paid

    declared_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
