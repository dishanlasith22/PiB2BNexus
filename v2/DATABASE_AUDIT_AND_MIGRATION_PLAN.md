# V2 Database Audit and Migration Plan

Audit date: 2026-11-17
Source: Supabase SQL Editor exports supplied by the project owner.
Scope: public-schema metadata only. No live database writes were performed.

## Findings confirmed by supplied exports

- The public schema includes these existing business tables: dealers, shops, user_profiles, products, shop_stock, shop_sales, deliveries, daily_settlements, shop_branches, shop_staff, promotions_arrivals.
- The column export contained 91 rows. This is a column inventory, not a full database backup.
- The foreign-key export showed two relationships:
  - shop_staff.pi_username -> user_profiles.pi_username
  - shops.pi_username -> user_profiles.pi_username
- The policy export showed a policy named "Allow public access to user_profiles" with command ALL and role public. Its effective exposure must be tested before changing it.
- The trigger export returned no rows for public.
- The index export should be treated as a metadata snapshot only; confirm exact indexes and query plans before adding indexes. Do not drop existing indexes based only on this export.

## Important limitations

These exports do not contain row data, full table definitions, check constraints, RLS enablement state, grants, functions, sequences, storage policies, or a restorable backup. No claim is made that the database is fully backed up or fully secured.

## Business rules to preserve

- Dealer daily settlement is based on historical buying-cost snapshots for goods actually sold by each shop on the business date.
- Gross dealer due = sum(quantity sold * unit_cost_at_receipt).
- Platform fee = 0.5% of eligible gross sold-cost and is charged to dealers only.
- Dealer net = gross due less platform fee.
- Unsold stock remains outstanding shop-to-dealer credit.
- Refunds and voids create reversing ledger entries; posted financial rows are not edited or deleted.
- Settlement generation at 23:50 local time must be idempotent by shop, dealer, and business date.
- A payout is not marked paid until the Pi Platform confirms it.
- Wallet private keys must never be collected or held by the platform.

## Proposed V2 modules

1. Identity and role membership
2. Dealers and dealer product catalogue
3. Shops, branches, and staff
4. Product barcode identifiers
5. Goods receipts and inventory movements with unit-cost snapshots
6. POS sales and sale line items
7. Credit ledger
8. Payment intents and verified payment receipts
9. Dealer settlement batches and settlement ledger
10. Refunds and reversal ledger entries
11. Shop-customer loyalty membership and referrals
12. Append-only audit events

## Safe migration sequence

1. Obtain a restorable database backup or export before any production DDL.
2. Capture full schema metadata: columns, constraints, foreign keys, indexes, RLS enablement, policies, grants, triggers, functions, and sequences.
3. Map existing rows and identifiers to the V2 model; identify duplicates and nullable/invalid references.
4. Create additive V2 tables in a separate namespace/prefix; do not rename or drop legacy tables.
5. Add and validate indexes and foreign keys after data mapping.
6. Enable and test RLS for dealer/shop/customer ownership boundaries.
7. Run migrations in a non-production project first, with rollback scripts and tests.
8. Deploy the new web/API services separately; keep the legacy Streamlit app operational.
9. Backfill in controlled batches and verify row counts and financial totals.
10. Cut over only after reconciliation, Pi Testnet payment verification, and operational sign-off.

## Status

- [x] Initial public table/column inventory reviewed
- [x] Supplied public policy export reviewed
- [x] Supplied foreign-key export reviewed
- [x] Supplied index export reviewed
- [x] Public trigger query returned no rows
- [ ] Restorable backup verified
- [ ] Full grants/RLS/constraints/functions audit
- [ ] Existing rows mapped to V2
- [ ] Migration SQL authored and tested against a disposable database
- [ ] Production migration approved and scheduled

## Safety

This document is a plan only. It has not changed Supabase. Do not apply production migrations until a restorable backup exists and the full schema/data mapping has been reviewed.
