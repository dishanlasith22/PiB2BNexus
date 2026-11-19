-- Three-level customer referral reward ledger.
-- Rewards are recorded only for paid POS sales and remain pending until settlement.
create table if not exists public.nexus_customer_referral_rewards (
 id uuid primary key default gen_random_uuid(),
 shop_id uuid not null references public.nexus_shops(id) on delete cascade,
 sale_id uuid not null references public.nexus_sales(id) on delete cascade,
 beneficiary_customer_id uuid not null references public.nexus_customers(id) on delete cascade,
 referred_customer_id uuid not null references public.nexus_customers(id) on delete cascade,
 level smallint not null check (level between 1 and 3),
 commission_rate numeric(6,5) not null check (commission_rate >= 0 and commission_rate <= 1),
 sale_total numeric(14,4) not null check (sale_total >= 0),
 reward_amount numeric(14,4) not null check (reward_amount >= 0),
 status text not null default 'pending' check (status in ('pending','approved','paid','reversed')),
 created_at timestamptz not null default now(),
 unique (sale_id, level)
);
create index if not exists nexus_referral_rewards_beneficiary_idx
 on public.nexus_customer_referral_rewards(beneficiary_customer_id, shop_id, created_at desc);
create index if not exists nexus_referral_rewards_sale_idx
 on public.nexus_customer_referral_rewards(sale_id);
alter table public.nexus_customer_referral_rewards enable row level security;
revoke all on public.nexus_customer_referral_rewards from anon, authenticated;
