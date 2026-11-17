-- PIB2BNexus V2 - FIFO cost layers and atomic POS posting
-- TEST PROJECT ONLY after migrations 001 and 002. Never run on production yet.
-- API must authenticate the caller and authorize shop/branch membership first.

begin;

create table if not exists public.nexus_v2_cost_layers (
    id uuid primary key default gen_random_uuid(),
    receipt_item_id uuid not null references public.nexus_v2_goods_receipt_items(id),
    shop_id uuid not null references public.nexus_v2_shops(id),
    branch_id uuid not null references public.nexus_v2_branches(id),
    product_id uuid not null references public.nexus_v2_products(id),
    dealer_id uuid not null references public.nexus_v2_dealers(id),
    received_at timestamptz not null,
    original_quantity numeric(18,3) not null check (original_quantity > 0),
    remaining_quantity numeric(18,3) not null check (remaining_quantity >= 0),
    unit_cost numeric(18,4) not null check (unit_cost >= 0),
    created_at timestamptz not null default now(),
    unique (receipt_item_id, branch_id),
    check (remaining_quantity <= original_quantity)
);

create index if not exists nexus_v2_cost_layers_fifo_idx
    on public.nexus_v2_cost_layers (branch_id, product_id, received_at, id)
    where remaining_quantity > 0;

create table if not exists public.nexus_v2_sale_item_cost_allocations (
    id uuid primary key default gen_random_uuid(),
    sale_item_id uuid not null references public.nexus_v2_sale_items(id),
    cost_layer_id uuid not null references public.nexus_v2_cost_layers(id),
    quantity numeric(18,3) not null check (quantity > 0),
    unit_cost numeric(18,4) not null check (unit_cost >= 0),
    extended_cost numeric(18,4) not null check (extended_cost >= 0),
    created_at timestamptz not null default now()
);

create index if not exists nexus_v2_sale_cost_alloc_sale_idx
    on public.nexus_v2_sale_item_cost_allocations (sale_item_id);

alter table public.nexus_v2_cost_layers enable row level security;
alter table public.nexus_v2_sale_item_cost_allocations enable row level security;
revoke all on public.nexus_v2_cost_layers,
    public.nexus_v2_sale_item_cost_allocations from anon, authenticated;

-- Receipt posting is atomic: receipt, cost layers, stock projection, movement,
-- and dealer credit entry either all commit or all roll back.
create or replace function public.nexus_v2_post_goods_receipt(
    p_shop_id uuid, p_branch_id uuid, p_dealer_id uuid,
    p_received_by uuid, p_idempotency_key text, p_items jsonb
) returns uuid
language plpgsql security invoker
set search_path = ''
as $$
declare
    v_receipt_id uuid;
    v_item jsonb;
    v_product_id uuid;
    v_qty numeric(18,3);
    v_cost numeric(18,4);
    v_receipt_item_id uuid;
    v_product_dealer uuid;
begin
    if p_idempotency_key is null or length(trim(p_idempotency_key)) < 8 then
        raise exception 'A valid idempotency key is required';
    end if;
    if jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
        raise exception 'At least one receipt item is required';
    end if;

    perform pg_advisory_xact_lock(hashtextextended('receipt:' || p_shop_id::text || ':' || p_idempotency_key, 0));
    select id into v_receipt_id
    from public.nexus_v2_goods_receipts
    where external_reference = p_idempotency_key
      and shop_id = p_shop_id and dealer_id = p_dealer_id;
    if v_receipt_id is not null then return v_receipt_id; end if;

    if not exists (select 1 from public.nexus_v2_shops where id=p_shop_id and status='active')
       or not exists (select 1 from public.nexus_v2_branches where id=p_branch_id and shop_id=p_shop_id and status='active')
       or not exists (select 1 from public.nexus_v2_dealers where id=p_dealer_id and status='active') then
        raise exception 'Invalid or inactive shop, branch, or dealer';
    end if;

    insert into public.nexus_v2_goods_receipts
        (dealer_id, shop_id, branch_id, received_by_identity_id, status, external_reference)
    values (p_dealer_id, p_shop_id, p_branch_id, p_received_by, 'posted', p_idempotency_key)
    returning id into v_receipt_id;

    for v_item in select value from jsonb_array_elements(p_items)
    loop
        v_product_id := (v_item->>'product_id')::uuid;
        v_qty := (v_item->>'quantity')::numeric(18,3);
        v_cost := (v_item->>'unit_cost')::numeric(18,4);
        if v_qty <= 0 or v_cost < 0 then raise exception 'Invalid quantity or unit cost'; end if;

        select dealer_id into v_product_dealer
        from public.nexus_v2_products where id=v_product_id and status='active' for share;
        if v_product_dealer is distinct from p_dealer_id then
            raise exception 'Product % does not belong to this dealer', v_product_id;
        end if;

        insert into public.nexus_v2_goods_receipt_items(receipt_id,product_id,quantity,unit_cost_snapshot)
        values(v_receipt_id,v_product_id,v_qty,v_cost) returning id into v_receipt_item_id;

        insert into public.nexus_v2_cost_layers
            (receipt_item_id,shop_id,branch_id,product_id,dealer_id,received_at,original_quantity,remaining_quantity,unit_cost)
        values(v_receipt_item_id,p_shop_id,p_branch_id,v_product_id,p_dealer_id,now(),v_qty,v_qty,v_cost);

        insert into public.nexus_v2_inventory_balances(shop_id,branch_id,product_id,quantity_on_hand)
        values(p_shop_id,p_branch_id,v_product_id,v_qty)
        on conflict(branch_id,product_id) do update
        set quantity_on_hand=public.nexus_v2_inventory_balances.quantity_on_hand+excluded.quantity_on_hand,
            updated_at=now();

        insert into public.nexus_v2_inventory_movements
            (shop_id,branch_id,product_id,receipt_item_id,movement_type,quantity_delta,unit_cost_snapshot,idempotency_key)
        values(p_shop_id,p_branch_id,v_product_id,v_receipt_item_id,'receipt',v_qty,v_cost,
               p_idempotency_key || ':stock:' || v_product_id::text || ':' || v_receipt_item_id::text);

        insert into public.nexus_v2_credit_ledger
            (dealer_id,shop_id,receipt_id,entry_type,amount,idempotency_key)
        values(p_dealer_id,p_shop_id,v_receipt_id,'goods_received',round(v_qty*v_cost,4),
               p_idempotency_key || ':credit:' || v_receipt_item_id::text);
    end loop;
    return v_receipt_id;
end;
$$;

-- Atomic POS sale. Input prices are accepted from the authenticated shop API
-- after permission checks; production API should validate prices against its
-- configured shop price list before calling this function.
create or replace function public.nexus_v2_post_sale(
    p_shop_id uuid, p_branch_id uuid, p_cashier_identity_id uuid,
    p_customer_identity_id uuid, p_bill_number text, p_currency text,
    p_idempotency_key text, p_items jsonb
) returns uuid
language plpgsql security invoker
set search_path = ''
as $$
declare
    v_sale_id uuid;
    v_item jsonb;
    v_product_id uuid;
    v_qty numeric(18,3);
    v_price numeric(18,4);
    v_dealer_id uuid;
    v_remaining numeric(18,3);
    v_take numeric(18,3);
    v_layer record;
    v_sale_item_id uuid;
    v_total_cost numeric(18,4);
    v_total_line numeric(18,4);
    v_subtotal numeric(18,4) := 0;
    v_allocations jsonb;
    v_allocation jsonb;
begin
    if p_idempotency_key is null or length(trim(p_idempotency_key)) < 8 then
        raise exception 'A valid idempotency key is required';
    end if;
    if p_bill_number is null or length(trim(p_bill_number))=0 then
        raise exception 'Bill number is required';
    end if;
    if jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items)=0 then
        raise exception 'At least one sale item is required';
    end if;

    perform pg_advisory_xact_lock(hashtextextended('sale:' || p_shop_id::text || ':' || p_idempotency_key,0));
    select id into v_sale_id from public.nexus_v2_sales where idempotency_key=p_idempotency_key;
    if v_sale_id is not null then return v_sale_id; end if;

    if not exists(select 1 from public.nexus_v2_shops where id=p_shop_id and status='active')
       or not exists(select 1 from public.nexus_v2_branches where id=p_branch_id and shop_id=p_shop_id and status='active') then
        raise exception 'Invalid or inactive shop/branch';
    end if;

    -- Lock all involved inventory rows in stable product-id order to reduce deadlocks.
    for v_product_id in
        select distinct (value->>'product_id')::uuid
        from jsonb_array_elements(p_items)
        order by 1
    loop
        perform 1 from public.nexus_v2_inventory_balances
        where shop_id=p_shop_id and branch_id=p_branch_id and product_id=v_product_id
        for update;
        if not found then raise exception 'No inventory record for product %',v_product_id; end if;
    end loop;

    insert into public.nexus_v2_sales
        (shop_id,branch_id,cashier_identity_id,customer_identity_id,bill_number,currency,
         subtotal,discount_total,total_amount,idempotency_key,status)
    values(p_shop_id,p_branch_id,p_cashier_identity_id,p_customer_identity_id,p_bill_number,
           coalesce(nullif(p_currency,''),'PI'),0,0,0,p_idempotency_key,'draft')
    returning id into v_sale_id;

    for v_item in select value from jsonb_array_elements(p_items)
    loop
        v_product_id := (v_item->>'product_id')::uuid;
        v_qty := (v_item->>'quantity')::numeric(18,3);
        v_price := (v_item->>'unit_selling_price')::numeric(18,4);
        if v_qty <= 0 or v_price < 0 then raise exception 'Invalid sale quantity or price'; end if;

        select dealer_id into v_dealer_id
        from public.nexus_v2_products where id=v_product_id and status='active' for share;
        if v_dealer_id is null then raise exception 'Unknown or inactive product %',v_product_id; end if;

        update public.nexus_v2_inventory_balances
        set quantity_on_hand=quantity_on_hand-v_qty,updated_at=now()
        where shop_id=p_shop_id and branch_id=p_branch_id and product_id=v_product_id
          and quantity_on_hand>=v_qty;
        if not found then raise exception 'Insufficient stock for product %',v_product_id; end if;

        v_remaining := v_qty;
        v_total_cost := 0;
        v_allocations := '[]'::jsonb;

        for v_layer in
            select id,remaining_quantity,unit_cost
            from public.nexus_v2_cost_layers
            where branch_id=p_branch_id and product_id=v_product_id and remaining_quantity>0
            order by received_at,id
            for update
        loop
            exit when v_remaining<=0;
            v_take := least(v_remaining,v_layer.remaining_quantity);
            update public.nexus_v2_cost_layers
            set remaining_quantity=remaining_quantity-v_take where id=v_layer.id;
            v_total_cost := v_total_cost+round(v_take*v_layer.unit_cost,4);
            v_allocations := v_allocations || jsonb_build_array(jsonb_build_object(
                'layer_id',v_layer.id,'quantity',v_take,'unit_cost',v_layer.unit_cost,
                'extended_cost',round(v_take*v_layer.unit_cost,4)));
            v_remaining := v_remaining-v_take;
        end loop;
        if v_remaining>0 then raise exception 'FIFO layers do not cover inventory balance for product %',v_product_id; end if;

        v_total_line := round(v_qty*v_price,4);
        insert into public.nexus_v2_sale_items
            (sale_id,product_id,dealer_id,quantity,unit_selling_price,unit_cost_snapshot,line_total)
        values(v_sale_id,v_product_id,v_dealer_id,v_qty,v_price,round(v_total_cost/v_qty,4),v_total_line)
        returning id into v_sale_item_id;

        for v_allocation in select value from jsonb_array_elements(v_allocations)
        loop
            insert into public.nexus_v2_sale_item_cost_allocations
                (sale_item_id,cost_layer_id,quantity,unit_cost,extended_cost)
            values(v_sale_item_id,(v_allocation->>'layer_id')::uuid,
                   (v_allocation->>'quantity')::numeric,
                   (v_allocation->>'unit_cost')::numeric,
                   (v_allocation->>'extended_cost')::numeric);
        end loop;

        insert into public.nexus_v2_inventory_movements
            (shop_id,branch_id,product_id,sale_item_id,movement_type,quantity_delta,unit_cost_snapshot,idempotency_key)
        values(p_shop_id,p_branch_id,v_product_id,v_sale_item_id,'sale',-v_qty,
               round(v_total_cost/v_qty,4),p_idempotency_key || ':stock:' || v_sale_item_id::text);

        insert into public.nexus_v2_credit_ledger
            (dealer_id,shop_id,sale_id,entry_type,amount,idempotency_key)
        values(v_dealer_id,p_shop_id,v_sale_id,'sold_cost_due',round(v_total_cost,4),
               p_idempotency_key || ':soldcost:' || v_sale_item_id::text);

        v_subtotal := v_subtotal+v_total_line;
    end loop;

    update public.nexus_v2_sales
    set subtotal=v_subtotal,total_amount=v_subtotal,status='completed'
    where id=v_sale_id;
    return v_sale_id;
end;
$$;

commit;
