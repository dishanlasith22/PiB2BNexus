# PIB2BNexus V2

Scale-first rebuild, isolated from the current Streamlit application.

## Services
- `web/`: Next.js + TypeScript user interface.
- `api/`: FastAPI application for verified identity, business workflows and payment orchestration.
- `db/migrations/`: reviewed SQL migration drafts. These files are **not** applied automatically.

## Non-negotiable financial rules
- Dealer settlement is based on the historical buying-cost snapshot of dealer goods actually sold by each shop during the business day.
- Unsold goods remain in the shop's outstanding dealer-credit balance.
- Ecosystem fee: 0.5% of eligible sold-cost, charged to dealers only.
- Refunds/voids must create reversing ledger entries; never edit or delete posted financial entries.
- A settlement is not marked paid until Pi Platform confirms the transaction.
- Referral rewards: 1% of eligible purchases by each of a customer's two referred customers, subject to the shop-specific referral relationship and a single agreed calculation base.

## Safety
- Existing Streamlit and FastAPI services remain untouched.
- Never put Pi private keys or Supabase service-role keys in browser code.
- Do not trust UID, username, bill amount, product price or wallet address supplied by a QR code or browser.
- Do not run migration SQL against production until a database backup and live schema review are complete.
- Pi automatic payouts remain gated on validating the supported Pi Platform authorization and transfer flow in Testnet.

## Local development
API:
```bash
cd v2/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Web:
```bash
cd v2/web
npm install
npm run dev
```
