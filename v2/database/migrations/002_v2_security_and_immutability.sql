-- PIB2BNexus V2 - restrictive access baseline and append-only protections
-- TEST PROJECT ONLY until a restorable backup and full access review exist.
-- The FastAPI backend must use a server-only Supabase service role key.
-- Never put the service role key in the browser or commit it to Git.
--
-- This intentionally denies direct anon/authenticated table access. A later
-- migration may add narrowly-scoped policies only after identity mapping and
-- ownership checks are implemented and tested. service_role bypasses RLS.

begin;

create or replace function public.nexus_v2_reject_mutation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception 'Append-only record: % is not permitted on %',
        tg_op, tg_table_name
        using errcode = '55000';
end;
$$;

-- Enable RLS on every V2 table. No client-facing policies are created here.
alter table public.nexus_v2_identities enable row level security;
alter table public.nexus_v2_dealers enable row level security;
alter table public.nexus_v2_shops enable row level security;
alter table public.nexus_v2_shop_memberships enable row level security;
alter table public.nexus_v2_branches enable row level security;
alter table public.nexus_v2_products enable row level security;
alter table public.nexus_v2_barcodes enable row level security;
alter table public.nexus_v2_goods_receipts enable row level security;
alter table public.nexus_v2_goods_receipt_items enable row level security;
alter table public.nexus_v2_inventory_balances enable row level security;
alter table public.nexus_v2_inventory_movements enable row level security;
alter table public.nexus_v2_sales enable row level security;
alter table public.nexus_v2_sale_items enable row level security;
alter table public.nexus_v2_credit_ledger enable row level security;
alter table public.nexus_v2_payment_records enable row level security;
alter table public.nexus_v2_settlement_batches enable row level security;
alter table public.nexus_v2_settlement_items enable row level security;
alter table public.nexus_v2_refunds enable row level security;
alter table public.nexus_v2_refund_items enable row level security;
alter table public.nexus_v2_customers enable row level security;
alter table public.nexus_v2_loyalty_memberships enable row level security;
alter table public.nexus_v2_referrals enable row level security;
alter table public.nexus_v2_reward_ledger enable row level security;
alter table public.nexus_v2_audit_events enable row level security;

-- Explicitly remove direct grants from browser roles. Backend service_role access
-- is retained; it bypasses RLS by design and must be protected server-side.
revoke all on
    public.nexus_v2_identities,
    public.nexus_v2_dealers,
    public.nexus_v2_shops,
    public.nexus_v2_shop_memberships,
    public.nexus_v2_branches,
    public.nexus_v2_products,
    public.nexus_v2_barcodes,
    public.nexus_v2_goods_receipts,
    public.nexus_v2_goods_receipt_items,
    public.nexus_v2_inventory_balances,
    public.nexus_v2_inventory_movements,
    public.nexus_v2_sales,
    public.nexus_v2_sale_items,
    public.nexus_v2_credit_ledger,
    public.nexus_v2_payment_records,
    public.nexus_v2_settlement_batches,
    public.nexus_v2_settlement_items,
    public.nexus_v2_refunds,
    public.nexus_v2_refund_items,
    public.nexus_v2_customers,
    public.nexus_v2_loyalty_memberships,
    public.nexus_v2_referrals,
    public.nexus_v2_reward_ledger,
    public.nexus_v2_audit_events
from anon, authenticated;

-- Protect immutable financial/history tables. Corrections must be represented
-- as new compensating rows, not edits/deletes of posted history.
do $$
declare
    t text;
    immutable_tables text[] := array[
        'nexus_v2_goods_receipt_items',
        'nexus_v2_inventory_movements',
        'nexus_v2_sale_items',
        'nexus_v2_credit_ledger',
        'nexus_v2_settlement_items',
        'nexus_v2_refund_items',
        'nexus_v2_reward_ledger',
        'nexus_v2_audit_events'
    ];
begin
    foreach t in array immutable_tables loop
        execute format(
            'drop trigger if exists %I on public.%I',
            t || '_immutable', t
        );
        execute format(
            'create trigger %I before update or delete on public.%I for each row execute function public.nexus_v2_reject_mutation()',
            t || '_immutable', t
        );
    end loop;
end;
$$;

commit;
