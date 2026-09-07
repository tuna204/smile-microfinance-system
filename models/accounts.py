from datetime import datetime
from extensions import db


class SavingsAccount(db.Model):
    """One savings account per member. balance is a CACHED total —
    it must only ever be changed by applying a Transaction, never
    edited directly. See services/ledger.py."""

    __tablename__ = "savings_accounts"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, unique=True)

    balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    share_capital_percent = db.Column(db.Numeric(5, 2), default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Loan(db.Model):
    """A loan application/record. status moves:
    pending -> approved -> disbursed -> (repaying) -> closed
    or pending -> rejected."""

    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)

    loan_type = db.Column(db.String(50), nullable=False)  # Personal, SME, Business, Agricultural, Emergency, Asset, Salary
    amount_requested = db.Column(db.Numeric(14, 2), nullable=False)
    amount_approved = db.Column(db.Numeric(14, 2))
    outstanding_balance = db.Column(db.Numeric(14, 2), default=0)

    status = db.Column(db.String(20), nullable=False, default="pending")
    # pending / approved / rejected / disbursed / closed

    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("members.id"))  # admin who acted
    reviewed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Investment(db.Model):
    """A fixed-tenor investment plan."""

    __tablename__ = "investments"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)

    principal_amount = db.Column(db.Numeric(14, 2), nullable=False)
    tenor_months = db.Column(db.Integer, nullable=False)  # 3, 6, or 12
    return_rate_percent = db.Column(db.Numeric(5, 2), nullable=False, default=2.0)

    status = db.Column(db.String(20), nullable=False, default="active")
    # active / matured / withdrawn / reinvested

    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    maturity_date = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def expected_return(self):
        return self.principal_amount * (self.return_rate_percent / 100)
