# V2 implementation status

Last reviewed: 2026-11-17
Branch: `feature/pib2bnexus-v2-foundation`

## Progress snapshot

**Foundation and design: about 25% complete. The working commerce application is not complete.**
This is a milestone estimate, not a measured delivery percentage. No POS-to-payment-to-settlement workflow has been implemented or verified end to end.

## Completed in GitHub

- [x] Isolated V2 Git branch created from `main`
- [x] Next.js + TypeScript frontend scaffold
- [x] FastAPI backend scaffold with health/info routes
- [x] Initial V2 dashboard placeholder
- [x] Initial requirements and developer README
- [x] Read-only review of the supplied Supabase public column, policy, foreign-key, index and trigger exports
- [x] Database audit and safe migration plan documented
- [x] Draft additive V2 core schema migration (`001_v2_core_foundation.sql`)
- [x] Draft restrictive access and append-only ledger migration (`002_v2_security_and_immutability.sql`)

## Not yet implemented or verified

- [ ] Restorable backup of the existing Supabase project
- [ ] Full database audit (grants, RLS enabled state, constraints, functions, sequences, data quality and actual data relationships)
- [ ] Run migrations in a separate disposable/test Supabase project
- [ ] Validate all SQL migrations and add rollback/recovery procedure
- [ ] Pi identity token verification and durable application sessions
- [ ] Dealer/shop/customer role and tenant ownership authorization
- [ ] Carefully scoped RLS policies and negative security tests
- [ ] Product catalogue and barcode management API/UI
- [ ] Goods receipt workflow and FIFO cost-layer allocation
- [ ] Transactional inventory balance and movement posting
- [ ] POS sale posting with atomic stock deduction and idempotency
- [ ] Customer Pi checkout and server-verified payment callbacks
- [ ] Dealer/shop credit balance and ledger workflows
- [ ] Refund/void flow with post-settlement reversal adjustments
- [ ] Daily 23:50 local-time dealer sold-cost settlement worker
- [ ] 0.5% dealer-only fee calculation, rounding rules and reconciliation
- [ ] Customer loyalty membership and per-shop referral cap/reward rules
- [ ] Audit event verification and operational monitoring
- [ ] Automated unit, integration, concurrency and end-to-end tests
- [ ] Testnet payment and settlement verification
- [ ] Render staging deployment and production cutover plan

## Safety and deployment status

- No Supabase schema or production data has been changed.
- The SQL migrations are committed as draft source files only; they have not been executed.
- The supplied CSV exports are metadata snapshots, not a restorable backup or a complete schema/security audit.
- No Pi payment or wallet transfer has been sent.
- No V2 service has been deployed or runtime-tested.
- The legacy Streamlit service remains separate and should stay operational during migration.

## Next execution order

1. Build a repeatable disposable test database environment and validate migrations there.
2. Implement backend identity verification and tenant authorization before exposing data routes.
3. Implement goods receipt + FIFO cost layers + transactional POS posting.
4. Implement refund reversals and settlement calculation/worker with deterministic test fixtures.
5. Integrate Pi Testnet payments only after the official supported flow is verified.
6. Build the corresponding frontend screens, run end-to-end tests, then deploy V2 staging on Render.
