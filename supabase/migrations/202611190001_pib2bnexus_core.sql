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

-- Food City demo tenant
insert into public.nexus_shops(shop_code,shop_name,address,phone,is_sample)
values ('FC-KDY-001','Food City','Kandy, Sri Lanka','0812000000',true)
on conflict(shop_code) do nothing;
insert into public.nexus_branches(shop_id,branch_code,branch_name,address,is_sample)
select s.id,v.code,v.name,v.address,true from public.nexus_shops s
cross join (values
 ('FC-MAIN','Food City - Main Branch','Kandy City Centre, Kandy'),
 ('FC-LAKE','Food City - Lake Road','Lake Road, Kandy'),
 ('FC-PERA','Food City - Peradeniya','Peradeniya, Kandy')
) v(code,name,address) where s.shop_code='FC-KDY-001' on conflict(branch_code) do nothing;

insert into public.nexus_dealers(dealer_code,business_name,phone,address,is_sample)
select 'DL-'||lpad(g::text,3,'0'), name, '077100'||lpad(g::text,4,'0'), 'Kandy, Sri Lanka', true
from generate_series(1,20) g
cross join lateral (select (array['Lanka Foods Wholesale','Fresh Supply Distributors','Central Grocery Traders','Hill Country Foods'])[1+((g-1)%4)] as name) n
on conflict(dealer_code) do nothing;

insert into public.nexus_products(dealer_id,sku,barcode,product_name,category,unit,wholesale_price,retail_price,image_url,is_sample)
select d.id, 'FC-SKU-'||lpad(g::text,4,'0'), '479'||lpad((100000000+g)::text,10,'0'),
 (array['White Rice 5kg','Coconut Oil 1L','Fresh Milk 1L','Milk Powder 400g','White Sugar 1kg','Black Tea 200g','Wheat Flour 1kg','Red Lentils 1kg','Butter 200g','Bread 450g','Eggs 10 Pack','Mineral Water 1.5L','Orange Juice 1L','Biscuits 200g','Tomato Sauce 400g','Dishwashing Liquid 500ml','Laundry Detergent 1kg','Toilet Tissue 4 Pack','Instant Noodles 5 Pack','Canned Fish 425g'])[g],
 (array['Rice & Grains','Cooking Essentials','Dairy','Dairy','Grocery','Beverages','Baking','Grocery','Dairy','Bakery','Fresh Food','Beverages','Beverages','Snacks','Condiments','Household','Household','Household','Instant Food','Canned Food'])[g],
 'each', round((1.00+g*0.37)::numeric,2), round((1.35+g*0.49)::numeric,2),
 (array[
 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=900',
 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=900',
 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=900',
 'https://images.unsplash.com/photo-1628088062854-d1870b4553da?w=900',
 'https://images.unsplash.com/photo-1581441363689-1f3c3c414635?w=900',
 'https://images.unsplash.com/photo-1544787219-7f47af3fc05b?w=900',
 'https://images.unsplash.com/photo-1627485937980-221c88ac04f9?w=900',
 'https://images.unsplash.com/photo-1515543904379-3d7576129fca?w=900',
 'https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=900',
 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=900',
 'https://images.unsplash.com/photo-1506976785307-8732e854ad03?w=900',
 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=900',
 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=900',
 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=900',
 'https://images.unsplash.com/photo-1472476443507-c7a5948772fc?w=900',
 'https://images.unsplash.com/photo-1585421514738-01798e348b17?w=900',
 'https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=900',
 'https://images.unsplash.com/photo-1584556812952-905ffd0c611a?w=900',
 'https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=900',
 'https://images.unsplash.com/photo-1547592180-85f173990554?w=900'
 ])[g], true
from public.nexus_dealers d cross join generate_series(1,20) g
where d.dealer_code='DL-'||lpad((1+((g-1)%20))::text,3,'0')
on conflict(sku) do nothing;

insert into public.nexus_inventory(branch_id,product_id,quantity,reorder_level,is_sample)
select b.id,p.id, 12+((row_number() over(order by p.sku,b.branch_code)*7)%90), 10, true
from public.nexus_branches b cross join public.nexus_products p
where b.branch_code='FC-MAIN'
on conflict(branch_id,product_id) do nothing;

insert into public.nexus_customers(pi_username,display_name,is_sample)
select 'foodcity_customer_'||lpad(g::text,2,'0'), 'Food City Customer '||lpad(g::text,2,'0'), true
from generate_series(1,20) g
on conflict(pi_uid) do nothing;

insert into public.nexus_promotions(shop_id,product_id,title,description,image_url,original_price,offer_price,starts_at,ends_at,status,is_sample)
select s.id,p.id,p.product_name||' - Weekly Special','Special price at Food City. While stocks last.',
 p.image_url,p.retail_price,round((p.retail_price*0.90)::numeric,2),current_date,current_date+7,'active',true
from public.nexus_shops s join public.nexus_products p on p.sku in
 ('FC-SKU-0001','FC-SKU-0002','FC-SKU-0003','FC-SKU-0004','FC-SKU-0005','FC-SKU-0006','FC-SKU-0007','FC-SKU-0008','FC-SKU-0009','FC-SKU-0010','FC-SKU-0011','FC-SKU-0012','FC-SKU-0013','FC-SKU-0014','FC-SKU-0015','FC-SKU-0016','FC-SKU-0017','FC-SKU-0018','FC-SKU-0019','FC-SKU-0020')
where s.shop_code='FC-KDY-001' on conflict do nothing;

insert into public.nexus_orders(order_no,shop_id,branch_id,dealer_id,status,total_cost,is_sample)
select 'FC-PO-'||lpad(g::text,4,'0'),s.id,b.id,d.id,
 (array['requested','approved','dispatched','received'])[1+((g-1)%4)],
 round((25+g*4.75)::numeric,2),true
from generate_series(1,20) g
join public.nexus_shops s on s.shop_code='FC-KDY-001'
join public.nexus_branches b on b.branch_code='FC-MAIN'
join public.nexus_dealers d on d.dealer_code='DL-'||lpad(g::text,3,'0')
on conflict(order_no) do nothing;

insert into public.nexus_sales(receipt_no,shop_id,branch_id,customer_id,subtotal,discount,total,payment_method,payment_status,is_sample)
select 'FC-SALE-'||lpad(g::text,4,'0'),s.id,b.id,c.id,
 round((8+g*2.15)::numeric,2),0,round((8+g*2.15)::numeric,2),
 (array['Pi','Cash','Card'])[1+((g-1)%3)],'paid',true
from generate_series(1,20) g
join public.nexus_shops s on s.shop_code='FC-KDY-001'
join public.nexus_branches b on b.branch_code='FC-MAIN'
join public.nexus_customers c on c.pi_username='foodcity_customer_'||lpad(g::text,2,'0')
on conflict(receipt_no) do nothing;

insert into public.nexus_settlements(settlement_no,dealer_id,settlement_date,sold_cost,dealer_fee,net_payable,status,scheduled_at,is_sample)
select 'FC-SET-'||lpad(g::text,4,'0'),d.id,current_date,
 round((12+g*1.8)::numeric,2),round((12+g*1.8)*0.005,2),
 round((12+g*1.8)*0.995,2),'scheduled',
 (current_date+time '23:50') at time zone 'Asia/Colombo',true
from generate_series(1,20) g join public.nexus_dealers d on d.dealer_code='DL-'||lpad(g::text,3,'0')
on conflict(settlement_no) do nothing;
