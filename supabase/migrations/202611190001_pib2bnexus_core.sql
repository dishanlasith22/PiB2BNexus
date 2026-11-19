-- PIB2BNexus core schema for Food City demo workspace.
-- Run in a NON-PRODUCTION Supabase project first. All sample rows are marked is_sample=true.
create extension if not exists pgcrypto;

create table if not exists public.nexus_shops (
 id uuid primary key default gen_random_uuid(), shop_code text unique not null, shop_name text not null,
 owner_pi_uid text, address text, phone text, is_sample boolean not null default false, created_at timestamptz default now()
);
create table if not exists public.nexus_branches (
 id uuid primary key default gen_random_uuid(), shop_id uuid not null references public.nexus_shops(id) on delete cascade,
 branch_code text unique not null, branch_name text not null, address text, is_sample boolean not null default false, created_at timestamptz default now()
);
create table if not exists public.nexus_dealers (
 id uuid primary key default gen_random_uuid(), dealer_code text unique not null, business_name text not null,
 pi_uid text, phone text, address text, fee_rate numeric(6,5) not null default 0.005,
 is_sample boolean not null default false, created_at timestamptz default now()
);
create table if not exists public.nexus_products (
 id uuid primary key default gen_random_uuid(), dealer_id uuid references public.nexus_dealers(id),
 sku text unique not null, barcode text unique, product_name text not null, category text not null,
 unit text not null default 'each', wholesale_price numeric(14,4) not null default 0,
 retail_price numeric(14,4) not null default 0, image_url text, is_active boolean not null default true,
 is_sample boolean not null default false, created_at timestamptz default now()
);
create table if not exists public.nexus_inventory (
 id uuid primary key default gen_random_uuid(), branch_id uuid not null references public.nexus_branches(id),
 product_id uuid not null references public.nexus_products(id), quantity numeric(14,3) not null default 0,
 reorder_level numeric(14,3) not null default 0, updated_at timestamptz default now(),
 is_sample boolean not null default false, unique(branch_id,product_id)
);
create table if not exists public.nexus_customers (
 id uuid primary key default gen_random_uuid(), pi_uid text unique, pi_username text not null,
 display_name text, phone text, is_sample boolean not null default false, created_at timestamptz default now()
);
create table if not exists public.nexus_promotions (
 id uuid primary key default gen_random_uuid(), shop_id uuid not null references public.nexus_shops(id),
 product_id uuid references public.nexus_products(id), title text not null, description text,
 image_url text not null, original_price numeric(14,4), offer_price numeric(14,4) not null,
 starts_at date not null, ends_at date not null, status text not null default 'draft',
 is_sample boolean not null default false, created_at timestamptz default now(),
 check (offer_price >= 0), check (ends_at >= starts_at)
);
create table if not exists public.nexus_orders (
 id uuid primary key default gen_random_uuid(), order_no text unique not null,
 shop_id uuid not null references public.nexus_shops(id), branch_id uuid references public.nexus_branches(id),
 dealer_id uuid not null references public.nexus_dealers(id), status text not null default 'requested',
 total_cost numeric(14,4) not null default 0, requested_at timestamptz default now(),
 is_sample boolean not null default false
);
create table if not exists public.nexus_sales (
 id uuid primary key default gen_random_uuid(), receipt_no text unique not null,
 shop_id uuid not null references public.nexus_shops(id), branch_id uuid not null references public.nexus_branches(id),
 customer_id uuid references public.nexus_customers(id), subtotal numeric(14,4) not null,
 discount numeric(14,4) not null default 0, total numeric(14,4) not null,
 payment_method text not null, payment_status text not null default 'pending',
 pi_payment_id text, sold_at timestamptz default now(), is_sample boolean not null default false
);
create table if not exists public.nexus_settlements (
 id uuid primary key default gen_random_uuid(), settlement_no text unique not null,
 dealer_id uuid not null references public.nexus_dealers(id), settlement_date date not null,
 sold_cost numeric(14,4) not null default 0, dealer_fee numeric(14,4) not null default 0,
 net_payable numeric(14,4) not null default 0, status text not null default 'scheduled',
 scheduled_at timestamptz, is_sample boolean not null default false
);
create table if not exists public.nexus_ledger (
 id uuid primary key default gen_random_uuid(), event_key text unique not null, event_type text not null,
 shop_id uuid references public.nexus_shops(id), branch_id uuid references public.nexus_branches(id),
 dealer_id uuid references public.nexus_dealers(id), product_id uuid references public.nexus_products(id),
 quantity_delta numeric(14,3) not null default 0, unit_cost numeric(14,4) not null default 0,
 reference_type text, reference_id uuid, reversal_of uuid references public.nexus_ledger(id),
 created_at timestamptz default now(), is_sample boolean not null default false
);

create index if not exists nexus_inventory_branch_idx on public.nexus_inventory(branch_id);
create index if not exists nexus_promotions_active_idx on public.nexus_promotions(status,starts_at,ends_at);
create index if not exists nexus_sales_branch_date_idx on public.nexus_sales(branch_id,sold_at);
create index if not exists nexus_ledger_product_date_idx on public.nexus_ledger(product_id,created_at);

-- Deny direct browser access. The FastAPI server uses the Supabase service-role key
-- only after verifying its signed Pi app session and enforcing ownership.
do $$ declare t text; begin
 foreach t in array array['nexus_shops','nexus_branches','nexus_dealers','nexus_products','nexus_inventory','nexus_customers','nexus_promotions','nexus_orders','nexus_sales','nexus_settlements','nexus_ledger'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from anon, authenticated',t);
 end loop;
end $$;

-- Demo rows are inserted by 202611190002_hackathon_demo_seed.sql so the test project has exactly 20 shops.
