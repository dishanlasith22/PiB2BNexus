-- PIB2BNexus V2 - additive core schema foundation
-- PostgreSQL / Supabase
-- IMPORTANT:
--   * This migration is NOT applied to production.
--   * Run only in a disposable/test Supabase project after reviewing it.
--   * All objects are prefixed nexus_v2_ to avoid collisions with legacy tables.
--   * No legacy table is altered, renamed, or dropped.
--   * RLS policies are intentionally not enabled here: ownership and Pi identity
--     verification must be implemented and tested before exposing these tables.
--   * Financial records are append-only by application policy; enforce with
--     restricted DB grants/triggers in a later security migration.

begin;

create extension if not exists pgcrypto;

-- Verified application identity is populated only by the API after validating
-- a Pi Platform identity token. Never accept pi_uid/username from browser input.
create table if not exists public.nexus_v2_identities (
    id uuid primary key default gen_random_uuid(),
    pi_uid text not null unique,
    pi_username text,
    verified_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_dealers (
    id uuid primary key default gen_random_uuid(),
    identity_id uuid not null references public.nexus_v2_identities(id),
    display_name text not null,
    status text not null default 'pending'
        check (status in ('pending','active','suspended','closed')),
    wallet_address text,
    wallet_verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (identity_id)
);

create table if not exists public.nexus_v2_shops (
    id uuid primary key default gen_random_uuid(),
    owner_identity_id uuid not null references public.nexus_v2_identities(id),
    name text not null,
    status text not null default 'active'
        check (status in ('active','suspended','closed')),
    wallet_address text,
    wallet_verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_shop_memberships (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    identity_id uuid not null references public.nexus_v2_identities(id),
    role text not null check (role in ('owner','manager','cashier','inventory')),
    status text not null default 'active' check (status in ('invited','active','disabled')),
    created_at timestamptz not null default now(),
    unique (shop_id, identity_id)
);

create table if not exists public.nexus_v2_branches (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    name text not null,
    code text,
    address jsonb not null default '{}'::jsonb,
    status text not null default 'active' check (status in ('active','closed')),
    created_at timestamptz not null default now(),
    unique (shop_id, code)
);

create table if not exists public.nexus_v2_products (
    id uuid primary key default gen_random_uuid(),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    sku text,
    name text not null,
    description text,
    unit text not null default 'unit',
    status text not null default 'active' check (status in ('active','archived')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (dealer_id, sku)
);

create table if not exists public.nexus_v2_barcodes (
    id uuid primary key default gen_random_uuid(),
    product_id uuid not null references public.nexus_v2_products(id),
    barcode text not null unique,
    barcode_type text not null default 'CODE128',
    created_at timestamptz not null default now()
);

-- A shop receiving dealer goods records the cost at receipt time. This immutable
-- unit_cost_snapshot is the basis for later sold-cost settlement calculations.
create table if not exists public.nexus_v2_goods_receipts (
    id uuid primary key default gen_random_uuid(),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    shop_id uuid not null references public.nexus_v2_shops(id),
    branch_id uuid references public.nexus_v2_branches(id),
    received_by_identity_id uuid references public.nexus_v2_identities(id),
    status text not null default 'posted' check (status in ('draft','posted','voided')),
    received_at timestamptz not null default now(),
    external_reference text,
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_goods_receipt_items (
    id uuid primary key default gen_random_uuid(),
    receipt_id uuid not null references public.nexus_v2_goods_receipts(id),
    product_id uuid not null references public.nexus_v2_products(id),
    quantity numeric(18,3) not null check (quantity > 0),
    unit_cost_snapshot numeric(18,4) not null check (unit_cost_snapshot >= 0),
    created_at timestamptz not null default now()
);

-- Inventory is derived from movements; balance is a transactional projection.
create table if not exists public.nexus_v2_inventory_balances (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    branch_id uuid not null references public.nexus_v2_branches(id),
    product_id uuid not null references public.nexus_v2_products(id),
    quantity_on_hand numeric(18,3) not null default 0 check (quantity_on_hand >= 0),
    updated_at timestamptz not null default now(),
    unique (branch_id, product_id)
);

create table if not exists public.nexus_v2_inventory_movements (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    branch_id uuid not null references public.nexus_v2_branches(id),
    product_id uuid not null references public.nexus_v2_products(id),
    receipt_item_id uuid references public.nexus_v2_goods_receipt_items(id),
    sale_item_id uuid,
    movement_type text not null check (movement_type in
        ('receipt','sale','sale_refund','adjustment_in','adjustment_out','transfer_in','transfer_out')),
    quantity_delta numeric(18,3) not null check (quantity_delta <> 0),
    unit_cost_snapshot numeric(18,4) check (unit_cost_snapshot is null or unit_cost_snapshot >= 0),
    idempotency_key text not null unique,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_sales (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    branch_id uuid not null references public.nexus_v2_branches(id),
    cashier_identity_id uuid references public.nexus_v2_identities(id),
    customer_identity_id uuid references public.nexus_v2_identities(id),
    bill_number text not null,
    status text not null default 'completed'
        check (status in ('draft','completed','voided','partially_refunded','refunded')),
    currency text not null default 'PI',
    subtotal numeric(18,4) not null check (subtotal >= 0),
    discount_total numeric(18,4) not null default 0 check (discount_total >= 0),
    total_amount numeric(18,4) not null check (total_amount >= 0),
    idempotency_key text not null unique,
    sold_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    unique (shop_id, bill_number)
);

create table if not exists public.nexus_v2_sale_items (
    id uuid primary key default gen_random_uuid(),
    sale_id uuid not null references public.nexus_v2_sales(id),
    product_id uuid not null references public.nexus_v2_products(id),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    quantity numeric(18,3) not null check (quantity > 0),
    unit_selling_price numeric(18,4) not null check (unit_selling_price >= 0),
    unit_cost_snapshot numeric(18,4) not null check (unit_cost_snapshot >= 0),
    line_total numeric(18,4) not null check (line_total >= 0),
    created_at timestamptz not null default now()
);

-- Append-only credit events. Balance is the sum of signed amounts.
create table if not exists public.nexus_v2_credit_ledger (
    id uuid primary key default gen_random_uuid(),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    shop_id uuid not null references public.nexus_v2_shops(id),
    receipt_id uuid references public.nexus_v2_goods_receipts(id),
    sale_id uuid references public.nexus_v2_sales(id),
    entry_type text not null check (entry_type in
        ('goods_received','sold_cost_due','payment','return','refund_adjustment','manual_adjustment')),
    amount numeric(18,4) not null,
    currency text not null default 'PI',
    idempotency_key text not null unique,
    reverses_entry_id uuid references public.nexus_v2_credit_ledger(id),
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_payment_records (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid references public.nexus_v2_shops(id),
    customer_identity_id uuid references public.nexus_v2_identities(id),
    dealer_id uuid references public.nexus_v2_dealers(id),
    payment_type text not null check (payment_type in ('customer_sale','dealer_settlement','shop_credit')),
    status text not null default 'created'
        check (status in ('created','submitted','approved','completed','failed','cancelled')),
    amount numeric(18,4) not null check (amount > 0),
    currency text not null default 'PI',
    pi_payment_id text unique,
    txid text unique,
    idempotency_key text not null unique,
    verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_settlement_batches (
    id uuid primary key default gen_random_uuid(),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    shop_id uuid not null references public.nexus_v2_shops(id),
    business_date date not null,
    currency text not null default 'PI',
    gross_sold_cost numeric(18,4) not null default 0 check (gross_sold_cost >= 0),
    platform_fee_rate numeric(8,6) not null default 0.005 check (platform_fee_rate = 0.005),
    platform_fee numeric(18,4) not null default 0 check (platform_fee >= 0),
    net_payout numeric(18,4) not null default 0 check (net_payout >= 0),
    status text not null default 'calculated'
        check (status in ('calculated','pending_payment','paid','failed','adjusted')),
    payment_record_id uuid references public.nexus_v2_payment_records(id),
    idempotency_key text not null unique,
    calculated_at timestamptz not null default now(),
    paid_at timestamptz,
    unique (dealer_id, shop_id, business_date)
);

create table if not exists public.nexus_v2_settlement_items (
    id uuid primary key default gen_random_uuid(),
    settlement_batch_id uuid not null references public.nexus_v2_settlement_batches(id),
    sale_item_id uuid not null references public.nexus_v2_sale_items(id),
    quantity_settled numeric(18,3) not null check (quantity_settled > 0),
    unit_cost_snapshot numeric(18,4) not null check (unit_cost_snapshot >= 0),
    gross_amount numeric(18,4) not null check (gross_amount >= 0),
    created_at timestamptz not null default now(),
    unique (settlement_batch_id, sale_item_id)
);

create table if not exists public.nexus_v2_refunds (
    id uuid primary key default gen_random_uuid(),
    sale_id uuid not null references public.nexus_v2_sales(id),
    requested_by_identity_id uuid references public.nexus_v2_identities(id),
    status text not null default 'requested'
        check (status in ('requested','approved','rejected','completed')),
    reason text,
    amount numeric(18,4) not null check (amount > 0),
    idempotency_key text not null unique,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create table if not exists public.nexus_v2_refund_items (
    id uuid primary key default gen_random_uuid(),
    refund_id uuid not null references public.nexus_v2_refunds(id),
    sale_item_id uuid not null references public.nexus_v2_sale_items(id),
    quantity numeric(18,3) not null check (quantity > 0),
    amount numeric(18,4) not null check (amount >= 0),
    cost_reversal_amount numeric(18,4) not null check (cost_reversal_amount >= 0),
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_customers (
    id uuid primary key default gen_random_uuid(),
    identity_id uuid not null unique references public.nexus_v2_identities(id),
    display_name text,
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_loyalty_memberships (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    customer_id uuid not null references public.nexus_v2_customers(id),
    status text not null default 'active' check (status in ('active','blocked','left')),
    joined_at timestamptz not null default now(),
    unique (shop_id, customer_id)
);

create table if not exists public.nexus_v2_referrals (
    id uuid primary key default gen_random_uuid(),
    shop_id uuid not null references public.nexus_v2_shops(id),
    referrer_customer_id uuid not null references public.nexus_v2_customers(id),
    referred_customer_id uuid not null references public.nexus_v2_customers(id),
    referral_code text not null unique,
    status text not null default 'pending' check (status in ('pending','qualified','blocked')),
    reward_rate numeric(8,6) not null default 0.01 check (reward_rate = 0.01),
    created_at timestamptz not null default now(),
    qualified_at timestamptz,
    check (referrer_customer_id <> referred_customer_id),
    unique (shop_id, referred_customer_id)
);

create table if not exists public.nexus_v2_reward_ledger (
    id uuid primary key default gen_random_uuid(),
    referral_id uuid not null references public.nexus_v2_referrals(id),
    customer_id uuid not null references public.nexus_v2_customers(id),
    sale_id uuid not null references public.nexus_v2_sales(id),
    amount numeric(18,4) not null check (amount >= 0),
    status text not null default 'pending' check (status in ('pending','approved','paid','reversed')),
    idempotency_key text not null unique,
    reverses_entry_id uuid references public.nexus_v2_reward_ledger(id),
    created_at timestamptz not null default now()
);

create table if not exists public.nexus_v2_audit_events (
    id uuid primary key default gen_random_uuid(),
    actor_identity_id uuid references public.nexus_v2_identities(id),
    entity_type text not null,
    entity_id uuid,
    action text not null,
    request_id text,
    before_data jsonb,
    after_data jsonb,
    previous_hash text,
    event_hash text,
    created_at timestamptz not null default now()
);

-- Query-path indexes. Validate with EXPLAIN and production-like data before rollout.
create index if not exists nexus_v2_products_dealer_idx
    on public.nexus_v2_products (dealer_id, status);
create index if not exists nexus_v2_receipts_shop_date_idx
    on public.nexus_v2_goods_receipts (shop_id, received_at desc);
create index if not exists nexus_v2_receipt_items_product_idx
    on public.nexus_v2_goods_receipt_items (product_id);
create index if not exists nexus_v2_inventory_shop_product_idx
    on public.nexus_v2_inventory_balances (shop_id, product_id);
create index if not exists nexus_v2_movements_product_date_idx
    on public.nexus_v2_inventory_movements (product_id, occurred_at desc);
create index if not exists nexus_v2_sales_shop_date_idx
    on public.nexus_v2_sales (shop_id, sold_at desc);
create index if not exists nexus_v2_sales_customer_date_idx
    on public.nexus_v2_sales (customer_identity_id, sold_at desc);
create index if not exists nexus_v2_sale_items_dealer_idx
    on public.nexus_v2_sale_items (dealer_id, sale_id);
create index if not exists nexus_v2_credit_shop_dealer_date_idx
    on public.nexus_v2_credit_ledger (shop_id, dealer_id, occurred_at desc);
create index if not exists nexus_v2_settlements_status_date_idx
    on public.nexus_v2_settlement_batches (status, business_date);
create index if not exists nexus_v2_referrals_referrer_idx
    on public.nexus_v2_referrals (referrer_customer_id, status);
create index if not exists nexus_v2_audit_entity_date_idx
    on public.nexus_v2_audit_events (entity_type, entity_id, created_at desc);

commit;
