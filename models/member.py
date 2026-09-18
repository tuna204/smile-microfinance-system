from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class Member(UserMixin, db.Model):
    """A registered cooperative member. Also doubles as the login account.

    Referral system: a member's own membership_no IS their referral code
    — no separate code needed. Someone registering via /membership?ref=<code>
    gets referred_by_id set to that member's id. When THAT referred member's
    registration fee is confirmed (see confirm_registration_fee), a ₦1,000
    referral bonus becomes owed to the referrer — paid out manually by
    admin to the referrer's own bank details (payout_account_number etc.),
    since this bonus is real cash leaving the cooperative, not a savings
    credit."""

    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    membership_no = db.Column(db.String(20), unique=True, nullable=False, index=True)

    full_name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    residential_address = db.Column(db.Text)
    occupation = db.Column(db.String(120))
    next_of_kin = db.Column(db.String(150))
    passport_photo_url = db.Column(db.String(255))

    savings_frequency = db.Column(db.String(20))  # Daily / Weekly / Monthly / Occasionally
    remarks = db.Column(db.Text)

    # Member's OWN bank account, for the cooperative to pay THEM —
    # referral bonuses, loan disbursements, dividends, etc. Nullable in
    # the DB so existing members aren't broken by this new column, but
    # required on the registration form going forward.
    payout_account_number = db.Column(db.String(20))
    payout_bank_name = db.Column(db.String(100))
    payout_account_name = db.Column(db.String(150))

    # Referral tracking — see class docstring.
    referred_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    referred_by = db.relationship("Member", remote_side=[id], foreign_keys=[referred_by_id])

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="member")

    is_active_member = db.Column(db.Boolean, default=False)
    registration_fee_paid = db.Column(db.Boolean, default=False)

    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    savings_account = db.relationship("SavingsAccount", backref="member", uselist=False)
    loans = db.relationship("Loan", foreign_keys="Loan.member_id", backref="member", lazy="dynamic")
    investments = db.relationship("Investment", backref="member", lazy="dynamic")
    transactions = db.relationship("Transaction", foreign_keys="Transaction.member_id", backref="member", lazy="dynamic")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<Member {self.membership_no} {self.full_name}>"
