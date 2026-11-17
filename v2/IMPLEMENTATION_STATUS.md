# V2 implementation status

Last reviewed: 2026-11-17
Branch: `feature/pib2bnexus-v2-foundation`

## Progress snapshot

**About 30% of the foundation/design and initial backend data-layer work is drafted. The working commerce application is not complete.**
This is a rough milestone estimate, not a measured feature-completion metric. No complete POS-to-payment-to-settlement workflow has been executed or verified.

## Completed in GitHub (source files only)

- [x] Isolated V2 Git branch created from `main`
- [x] Next.js + TypeScript frontend scaffold and starter dashboard
- [x] FastAPI backend scaffold with health/info routes
- [x] Initial developer README and API requirements
- [x] Read-only review of supplied Supabase public column, policy, foreign-key, index and trigger exports
- [x] Database audit and safe migration plan documented
- [x] Draft additive V2 core schema migration (`001_v2_core_foundation.sql`)
- [x] Draft restrictive RLS/access and append-only ledger migration (`002_v2_security_and_immutability.sql`)
- [x] Draft FIFO cost-layer schema and transactional goods-receipt/POS posting functions (`003_v2_fifo_cost_layers_and_pos.sql`)
- [x] POS RPC execution restricted to the backend service role in the migration draft

## Not yet implemented or verified

- [ ] Restorable backup of the existing Supabase project
- [ ] Full database audit (grants, RLS enabled state, constraints, functions, sequences, data quality and actual data relationships)
- [ ] Execute and validate migrations in a separate disposable/test Supabase project
- [ ] SQL linting, automated database tests and rollback/recovery procedure
- [ ] Backend API routes, input schemas and structured error handling for receipt/POS functions
- [ ] Pi identity token verification and durable application sessions
- [ ] Dealer/shop/customer role and tenant ownership authorization before RPC invocation
- [ ] Carefully scoped RLS policies and negative security tests
- [ ] Product catalogue and barcode management API/UI
- [ ] Goods receipt and FIFO allocation behavior verified with test fixtures
- [ ] POS sale posting verified for concurrency, duplicate requests and insufficient stock
- [ ] Customer Pi checkout and server-verified payment callbacks
- [ ] Dealer/shop credit balance and ledger workflows
- [ ] Refund/void flow with post-settlement reversal adjustments
- [ ] Daily 23:50 local-time dealer sold-cost settlement worker
- [ ] 0.5% dealer-only fee calculation, rounding rules and reconciliation
- [ ] Customer loyalty membership and per-shop referral cap/reward rules
- [ ] Audit event verification and operational monitoring
- [ ] Automated unit, integration, concurrency and end-to-end tests
- [ ] Pi Testnet payment and settlement verification
- [ ] Render staging deployment and production cutover plan

## Safety and deployment status

- No Supabase schema or production data has been changed.
- All SQL migrations are draft source files only; they have not been executed or runtime-tested.
- Supplied CSV exports are metadata snapshots, not a restorable backup or a complete schema/security audit.
- No Pi payment or wallet transfer has been sent.
- No V2 service has been deployed.
- The legacy Streamlit service remains separate and should stay operational during migration.

## Next execution order

1. Create a disposable test database and validate migrations 001-003.
2. Add automated SQL tests for receipt idempotency, FIFO allocation, stock locking, duplicate sale requests and rollback on failure.
3. Implement server-side identity verification and tenant authorization before exposing any business RPC.
4. Build/refine refunds, credit ledger and daily dealer settlement functions with test fixtures.
5. Integrate Pi Testnet payments only after verifying the supported official flow.
6. Build frontend workflows, run end-to-end tests, then deploy V2 staging on Render.
