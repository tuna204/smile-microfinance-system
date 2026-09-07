# Smile Cooperative - Backend (Flask)

## Payment reconciliation - how it actually works

A payment-gateway virtual-account approach was the first design, but it
was dropped: it requires Paystack (or similar) business KYC approval,
and even though the fee is capped at ₦2,000 max per transaction (not
uncapped, as first thought), that's still real money on every single
member deposit for a bootstrapped cooperative. That code has been
removed from this codebase to keep things lean — the notes below are
what's actually active.

**What's active now is fee-free:**

1. Every member gets a membership number on registration (e.g.
   `SM-2026-30916`) — shown on their dashboard as their payment reference
2. They transfer directly to the company bank account and put that
   number in the transfer description
3. Staff sees the bank alert like normal (SMS/banking app) and goes to
   `/admin/record-payment`, types the membership number + amount, hits
   confirm
4. That one click runs `services.ledger.record_deposit()` — balance
   updates, and email + SMS fire automatically

This is **semi-automatic**: the matching, balance update, and
notifications are all automatic once staff confirms — the only manual
step is staff glancing at the alert and typing two fields. Nothing
watches the bank account itself; that would require either a payment
gateway (which has fees) or a paid bank-data API like Mono/Okra (also
has costs, but no automatic detection is free — worth knowing if this
gets revisited later).

## What's built so far

- **Auth**: registration + login (Flask-Login, hashed passwords)
- **Models**: Member, SavingsAccount, Loan, Investment, Transaction (audit
  ledger), DividendPayout
- **Ledger service** (`services/ledger.py`): the ONLY code path allowed to
  change a balance — every change is logged as a Transaction row
- **Fee-free payment recording** (`routes/admin.py::record_payment`):
  staff confirms a bank transfer by membership number, triggers instant
  balance update + email/SMS — see "Payment reconciliation" above
- **Admin review queue** (`routes/admin.py`): large/first payments stay
  flagged for a human audit check even though they already reflect in
  the member's dashboard — the fraud-safety split we discussed

## Not yet built

- Loan application/approval workflow (model exists, no routes yet)
- Investment creation flow (model exists, no routes yet)
- Dividend batch creation for admin
- Real styling on dashboard/admin templates (currently bare-bones —
  once the logic is confirmed working, I'll match the navy/gold site design)

## Before going live: passport photo storage

Passport photos currently save to `static/uploads/passports/` on local
disk (see `routes/auth.py::_save_passport_photo`). This works for local
development, but **Railway's filesystem is ephemeral** — same issue as
the SQLite decision earlier. Every redeploy wipes uploaded files. Before
launch, swap this for an external storage service (Cloudinary's free
tier is simple to wire in) so member photos survive deployments.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in .env with real values (or leave mail settings blank for now —
# registration and login work without them)

export FLASK_APP=app.py
export FLASK_ENV=development

flask db init
flask db migrate -m "initial tables"
flask db upgrade

flask run
```

Visit `http://localhost:5000/auth/register` to create a test account.

## Deploying to Railway

1. Push this folder to a GitHub repo
2. On Railway: New Project → Deploy from GitHub repo
3. Add a PostgreSQL service to the same project (Railway auto-injects
   `DATABASE_URL` into your app's environment — no manual copying needed)
4. Set the other environment variables from `.env.example` under your
   app service's Variables tab
5. Railway auto-detects the `Procfile` and runs `gunicorn app:app`
6. After first deploy, run migrations from Railway's shell:
   `flask db upgrade`

## Making your first admin user

There's no signup flow for admins yet (intentional — you don't want that
public). After registering a normal account, promote it manually:

```sql
UPDATE members SET role = 'admin' WHERE email = 'director@example.com';
```

## Security notes for your director conversation

- Every balance change goes through `services/ledger.py` — nothing edits
  a balance directly from a route or the frontend
- Only staff with the `admin` role can access `/admin/record-payment` —
  enforced by the `admin_required` decorator, not just hiding the link
- Large payments (`REVIEW_THRESHOLD_NGN` in `ledger.py`, currently
  ₦500,000) stay flagged for admin review even though they reflect
  instantly — tune this number once real transaction volumes are known
- Passwords are hashed (never stored in plain text)
- `SESSION_COOKIE_SECURE` is on in production — cookies only travel over
  HTTPS (Railway gives you HTTPS automatically)
