-- Customer referral codes are scoped to the shop where the customer has completed a purchase.
create table if not exists public.nexus_customer_referral_codes (
 id uuid primary key default gen_random_uuid(),
 shop_id uuid not null references public.nexus_shops(id) on delete cascade,
 customer_id uuid not null references public.nexus_customers(id) on delete cascade,
 referral_code text not null unique,
 created_at timestamptz not null default now(),
 unique(shop_id, customer_id)
);
create table if not exists public.nexus_customer_referrals (
 id uuid primary key default gen_random_uuid(),
 shop_id uuid not null references public.nexus_shops(id) on delete cascade,
 referral_code_id uuid not null references public.nexus_customer_referral_codes(id),
 referrer_customer_id uuid not null references public.nexus_customers(id),
 referred_customer_id uuid not null references public.nexus_customers(id),
 created_at timestamptz not null default now(),
 constraint nexus_customer_referrals_no_self check (referrer_customer_id <> referred_customer_id),
 constraint nexus_customer_referrals_one_per_shop unique(shop_id, referred_customer_id)
);
create index if not exists nexus_referral_codes_customer_idx on public.nexus_customer_referral_codes(customer_id, shop_id);
create index if not exists nexus_referrals_referrer_idx on public.nexus_customer_referrals(referrer_customer_id, shop_id, created_at desc);
create index if not exists nexus_referrals_referred_idx on public.nexus_customer_referrals(referred_customer_id, shop_id);
alter table public.nexus_customer_referral_codes enable row level security;
alter table public.nexus_customer_referrals enable row level security;
revoke all on public.nexus_customer_referral_codes, public.nexus_customer_referrals from anon, authenticated;
