-- Hackathon demo seed pack v2. Run ONLY in a fresh TEST Supabase project,
-- after 202611190001_pib2bnexus_core.sql. Idempotent by stable sample codes.
-- Generates 20 shops, 10 dealers per shop, 10 products per dealer,
-- 20 customers per shop, 30 days of sales, and 23:50 Asia/Colombo settlements.

alter table public.nexus_shops add column if not exists shop_category text;
alter table public.nexus_dealers add column if not exists shop_id uuid references public.nexus_shops(id);
alter table public.nexus_customers add column if not exists home_shop_id uuid references public.nexus_shops(id);
alter table public.nexus_products add column if not exists shop_id uuid references public.nexus_shops(id);
alter table public.nexus_sales add column if not exists dealer_id uuid references public.nexus_dealers(id);
alter table public.nexus_sales add column if not exists transaction_day date;
alter table public.nexus_sales add column if not exists created_by text;

create table if not exists public.nexus_sale_items (
 id uuid primary key default gen_random_uuid(), sale_id uuid not null references public.nexus_sales(id) on delete cascade,
 product_id uuid not null references public.nexus_products(id), dealer_id uuid not null references public.nexus_dealers(id),
 quantity numeric(14,3) not null, unit_price numeric(14,4) not null, unit_cost_snapshot numeric(14,4) not null,
 line_total numeric(14,4) not null, is_sample boolean not null default false
);
create table if not exists public.nexus_stock_lots (
 id uuid primary key default gen_random_uuid(), shop_id uuid not null references public.nexus_shops(id),
 branch_id uuid not null references public.nexus_branches(id), dealer_id uuid not null references public.nexus_dealers(id),
 product_id uuid not null references public.nexus_products(id), received_at timestamptz not null,
 quantity_received numeric(14,3) not null, quantity_remaining numeric(14,3) not null,
 unit_cost numeric(14,4) not null, source_order_id uuid references public.nexus_orders(id),
 is_sample boolean not null default false
);
create table if not exists public.nexus_dealer_transactions (
 id uuid primary key default gen_random_uuid(), transaction_no text unique not null,
 dealer_id uuid not null references public.nexus_dealers(id), shop_id uuid not null references public.nexus_shops(id),
 transaction_date date not null, gross_sold_cost numeric(14,4) not null,
 dealer_fee_rate numeric(6,5) not null default 0.005, dealer_fee numeric(14,4) not null,
 net_payable numeric(14,4) not null, scheduled_at timestamptz not null,
 status text not null default 'scheduled', is_sample boolean not null default true,
 unique(dealer_id,shop_id,transaction_date)
);
create index if not exists nexus_sale_items_sale_idx on public.nexus_sale_items(sale_id);
create index if not exists nexus_stock_lots_fifo_idx on public.nexus_stock_lots(shop_id,product_id,received_at);
create index if not exists nexus_dealer_transactions_date_idx on public.nexus_dealer_transactions(transaction_date,scheduled_at);
alter table public.nexus_sale_items enable row level security;
alter table public.nexus_stock_lots enable row level security;
alter table public.nexus_dealer_transactions enable row level security;
revoke all on public.nexus_sale_items,public.nexus_stock_lots,public.nexus_dealer_transactions from anon,authenticated;

-- 20 English-named demo merchants across 9 retail categories.
with shop_seed as (
 select * from (values
 (1,'Food City Central','Grocery & Supermarket'),(2,'Fresh Basket Market','Grocery & Supermarket'),(3,'TechNova Computers','Computer Shop'),
 (4,'ByteBridge IT Store','Computer Shop'),(5,'AutoPro Vehicle Parts','Vehicle Parts'),(6,'MotorLine Spares','Vehicle Parts'),
 (7,'BrightWay Electricals','Electrical Items'),(8,'VoltEdge Electric Store','Electrical Items'),
 (9,'Crown Liquor Mart','Liquor Shop'),(10,'Cellar Select','Liquor Shop'),
 (11,'UrbanWeave Textiles','Textile Shop'),(12,'Loom & Thread Fashion','Textile Shop'),
 (13,'Royal Gems Jewellery','Jewellery Shop'),(14,'GoldenArc Jewellers','Jewellery Shop'),
 (15,'StepRight Shoes','Shoes Shop'),(16,'Sole Avenue Footwear','Shoes Shop'),
 (17,'Readers Corner Books','Book Shop'),(18,'PageTurner Book House','Book Shop'),
 (19,'DailyNeeds Supermarket','Grocery & Supermarket'),(20,'CityStyle Textiles','Textile Shop')
 ) as x(n,shop_name,category)
)
insert into public.nexus_shops(shop_code,shop_name,shop_category,address,phone,is_sample)
select 'HK-SHOP-'||lpad(n::text,3,'0'),shop_name,category,
 (array['Kandy','Colombo','Galle','Kurunegala','Matara','Negombo','Kegalle','Gampaha','Badulla','Jaffna'])[1+((n-1)%10)]||', Sri Lanka',
 '070'||lpad((1000000+n)::text,7,'0'),true from shop_seed
on conflict(shop_code) do update set shop_name=excluded.shop_name,shop_category=excluded.shop_category;

-- One branch per sample shop (Food City already has its demo branches).
insert into public.nexus_branches(shop_id,branch_code,branch_name,address,is_sample)
select s.id,'HK-BR-'||lpad(g::text,3,'0'),s.shop_name||' - Main Branch',s.address,true
from public.nexus_shops s join generate_series(1,20) g on s.shop_code='HK-SHOP-'||lpad(g::text,3,'0')
on conflict(branch_code) do nothing;

-- Exactly 10 dealer accounts per shop.
insert into public.nexus_dealers(dealer_code,business_name,shop_id,phone,address,fee_rate,is_sample)
select 'HK-DL-'||lpad(sno::text,3,'0')||'-'||lpad(dno::text,2,'0'),
 (array['Prime Wholesale','Global Trade Supplies','Metro Distributors','United Merchants','Summit Trading'])[1+((dno-1)%5)]
 ||' '||lpad(sno::text,2,'0'),s.id,'071'||lpad((sno*100+dno)::text,7,'0'),s.address,0.005,true
from generate_series(1,20) sno cross join generate_series(1,10) dno
join public.nexus_shops s on s.shop_code='HK-SHOP-'||lpad(sno::text,3,'0')
on conflict(dealer_code) do update set shop_id=excluded.shop_id,business_name=excluded.business_name;

-- 10 realistic category-matched catalogue products per dealer (2,000 total).
with catalog as (
 select * from (values
 ('Grocery & Supermarket',1,'Premium Basmati Rice 5kg','Grocery',7.20,8.50),
 ('Grocery & Supermarket',2,'Virgin Coconut Oil 1L','Cooking Oil',3.55,4.20),
 ('Grocery & Supermarket',3,'Full Cream Milk Powder 400g','Dairy',3.10,3.80),
 ('Grocery & Supermarket',4,'Brown Sugar 1kg','Grocery',1.20,1.55),
 ('Grocery & Supermarket',5,'Ceylon Black Tea 200g','Beverages',2.10,2.75),
 ('Grocery & Supermarket',6,'Red Dhal 1kg','Grocery',1.80,2.25),
 ('Grocery & Supermarket',7,'Fresh White Bread 450g','Bakery',0.85,1.10),
 ('Grocery & Supermarket',8,'Farm Fresh Eggs 10 Pack','Fresh Food',2.00,2.50),
 ('Grocery & Supermarket',9,'Orange Juice 1L','Beverages',1.45,1.90),
 ('Grocery & Supermarket',10,'Chocolate Cream Biscuits 200g','Snacks',0.75,1.05),
 ('Computer Shop',1,'Dell Inspiron 15 Laptop','Computers',510,585),
 ('Computer Shop',2,'HP Pavilion Desktop PC','Computers',620,710),
 ('Computer Shop',3,'Logitech Wireless Mouse','Accessories',12,16),
 ('Computer Shop',4,'Mechanical Gaming Keyboard','Accessories',35,45),
 ('Computer Shop',5,'Samsung 24-inch Monitor','Displays',105,125),
 ('Computer Shop',6,'Kingston 1TB SSD','Storage',68,82),
 ('Computer Shop',7,'Corsair 16GB DDR4 RAM','Components',38,48),
 ('Computer Shop',8,'TP-Link Wi-Fi 6 Router','Networking',52,65),
 ('Computer Shop',9,'Canon Inkjet Printer','Printers',95,115),
 ('Computer Shop',10,'Anker USB-C Hub 7-in-1','Accessories',24,32),
 ('Vehicle Parts',1,'Bosch Premium Brake Pads','Brakes',28,36),
 ('Vehicle Parts',2,'Denso Iridium Spark Plug','Engine Parts',8,11),
 ('Vehicle Parts',3,'Mobil 1 Synthetic Engine Oil 4L','Lubricants',32,40),
 ('Vehicle Parts',4,'Toyota Corolla Oil Filter','Filters',5,7),
 ('Vehicle Parts',5,'Amaron Car Battery 45Ah','Batteries',75,92),
 ('Vehicle Parts',6,'Michelin 185/65R15 Tyre','Tyres',82,99),
 ('Vehicle Parts',7,'Gates Timing Belt Kit','Engine Parts',45,56),
 ('Vehicle Parts',8,'Philips H4 Headlamp Bulb','Lighting',9,12),
 ('Vehicle Parts',9,'NGK Ignition Coil','Ignition',24,31),
 ('Vehicle Parts',10,'Valeo Clutch Kit','Transmission',110,132),
 ('Electrical Items',1,'Philips LED Bulb 12W','Lighting',2.2,3.0),
 ('Electrical Items',2,'Panasonic 2-Gang Power Socket','Switches',4.5,6.0),
 ('Electrical Items',3,'Schneider Miniature Circuit Breaker','Protection',8,11),
 ('Electrical Items',4,'Havells Ceiling Fan 56-inch','Appliances',48,59),
 ('Electrical Items',5,'TP-Link Smart Plug','Smart Home',12,16),
 ('Electrical Items',6,'Anchor 2.5mm Electrical Cable 10m','Cables',7,9),
 ('Electrical Items',7,'Legrand Distribution Board','Protection',22,28),
 ('Electrical Items',8,'Philips Rechargeable Emergency Light','Lighting',16,21),
 ('Electrical Items',9,'Panasonic Extension Cord 5m','Accessories',9,12),
 ('Electrical Items',10,'Hager Double Pole Isolator','Protection',18,23),
 ('Liquor Shop',1,'Johnnie Walker Black Label 750ml','Whisky',42,49),
 ('Liquor Shop',2,'Chivas Regal 12 Year 750ml','Whisky',38,45),
 ('Liquor Shop',3,'Absolut Vodka 750ml','Vodka',26,32),
 ('Liquor Shop',4,'Bombay Sapphire Gin 750ml','Gin',31,38),
 ('Liquor Shop',5,'Bacardi Carta Blanca 750ml','Rum',22,28),
 ('Liquor Shop',6,'Heineken Lager 330ml 6 Pack','Beer',9,12),
 ('Liquor Shop',7,'Jacob''s Creek Shiraz 750ml','Wine',14,18),
 ('Liquor Shop',8,'Martini Rosso Vermouth 750ml','Aperitif',15,19),
 ('Liquor Shop',9,'Baileys Original Irish Cream 700ml','Liqueur',25,31),
 ('Liquor Shop',10,'Captain Morgan Dark Rum 750ml','Rum',21,27),
 ('Textile Shop',1,'Premium Cotton Bed Sheet Set','Home Textiles',18,24),
 ('Textile Shop',2,'Printed Cotton Saree','Traditional Wear',22,30),
 ('Textile Shop',3,'Mens Oxford Formal Shirt','Menswear',12,17),
 ('Textile Shop',4,'Womens Linen Blouse','Womenswear',14,19),
 ('Textile Shop',5,'Cotton Bath Towel Set','Home Textiles',10,14),
 ('Textile Shop',6,'School Uniform Fabric 2m','Fabric',8,11),
 ('Textile Shop',7,'Denim Jeans Classic Fit','Menswear',20,27),
 ('Textile Shop',8,'Floral Cotton Dress','Womenswear',18,25),
 ('Textile Shop',9,'Wool Blend Winter Scarf','Accessories',7,10),
 ('Textile Shop',10,'Luxury Cushion Cover Pair','Home Textiles',6,9),
 ('Jewellery Shop',1,'18K Gold Chain 5g','Gold Jewellery',320,365),
 ('Jewellery Shop',2,'Sterling Silver Pendant','Silver Jewellery',28,36),
 ('Jewellery Shop',3,'Pearl Stud Earrings','Earrings',42,55),
 ('Jewellery Shop',4,'Gold Plated Bracelet','Bracelets',18,25),
 ('Jewellery Shop',5,'Classic Diamond Ring 0.25ct','Diamond Jewellery',450,520),
 ('Jewellery Shop',6,'Gemstone Sapphire Pendant','Gemstone Jewellery',85,105),
 ('Jewellery Shop',7,'Rose Gold Bangle','Gold Jewellery',140,165),
 ('Jewellery Shop',8,'Silver Charm Anklet','Silver Jewellery',16,22),
 ('Jewellery Shop',9,'Crystal Drop Earrings','Earrings',12,17),
 ('Jewellery Shop',10,'Traditional Wedding Necklace','Gold Jewellery',520,610),
 ('Shoes Shop',1,'Nike Air Max Running Shoes','Sports Shoes',68,82),
 ('Shoes Shop',2,'Adidas Ultraboost Trainers','Sports Shoes',85,99),
 ('Shoes Shop',3,'Bata Mens Formal Leather Shoes','Formal Shoes',32,42),
 ('Shoes Shop',4,'Clarks Womens Flat Shoes','Womens Shoes',38,48),
 ('Shoes Shop',5,'Puma Kids Velcro Sneakers','Kids Shoes',22,29),
 ('Shoes Shop',6,'Skechers Memory Foam Slip-ons','Casual Shoes',42,52),
 ('Shoes Shop',7,'Timberland Outdoor Boots','Boots',95,115),
 ('Shoes Shop',8,'Crocs Classic Clogs','Casual Shoes',28,35),
 ('Shoes Shop',9,'Reebok Training Shoes','Sports Shoes',45,56),
 ('Shoes Shop',10,'Hush Puppies School Shoes','School Shoes',25,33),
 ('Book Shop',1,'Oxford English Dictionary','Reference Books',24,30),
 ('Book Shop',2,'Cambridge IELTS Academic Guide','Education',18,24),
 ('Book Shop',3,'The Hobbit Paperback','Fiction',9,13),
 ('Book Shop',4,'Atomic Habits Hardcover','Self Help',14,19),
 ('Book Shop',5,'Introduction to Computer Science','Technology',28,36),
 ('Book Shop',6,'Sri Lankan History Illustrated','History',16,22),
 ('Book Shop',7,'Mathematics Workbook Grade 10','Education',6,9),
 ('Book Shop',8,'The Alchemist Paperback','Fiction',8,12),
 ('Book Shop',9,'National Geographic Atlas','Reference Books',22,29),
 ('Book Shop',10,'Business Management Essentials','Business',19,25)
 ) as c(category,seq,product_name,product_type,cost,price)
)
insert into public.nexus_products(dealer_id,shop_id,sku,barcode,product_name,category,unit,wholesale_price,retail_price,is_sample)
select d.id,d.shop_id,d.dealer_code||'-SKU-'||lpad(c.seq::text,2,'0'),
 '479'||lpad((700000000+row_number() over(order by d.dealer_code,c.seq))::text,10,'0'),
 c.product_name,c.product_type,'each',c.cost,c.price,true
from public.nexus_dealers d join public.nexus_shops s on s.id=d.shop_id
join catalog c on c.category=s.shop_category
on conflict(sku) do nothing;

-- 20 customers per shop, all English display names.
insert into public.nexus_customers(pi_uid,pi_username,display_name,home_shop_id,is_sample)
select 'sample-hk-'||lpad(sno::text,3,'0')||'-'||lpad(cno::text,2,'0'), 'hk_customer_'||lpad(sno::text,3,'0')||'_'||lpad(cno::text,2,'0'),
 (array['Alex Morgan','Jordan Lee','Taylor Smith','Casey Brown','Riley Wilson','Jamie Taylor','Avery Martin','Morgan Clark','Cameron Lewis','Drew Walker','Skyler Hall','Quinn Allen','Reese Young','Parker King','Rowan Wright','Emerson Scott','Hayden Green','Finley Baker','Dakota Adams','Harper Nelson'])[cno],
 s.id,true
from generate_series(1,20) sno cross join generate_series(1,20) cno
join public.nexus_shops s on s.shop_code='HK-SHOP-'||lpad(sno::text,3,'0')
on conflict(pi_uid) do nothing;

-- Opening stock lots per dealer/product: enough stock for the demo sales.
insert into public.nexus_stock_lots(shop_id,branch_id,dealer_id,product_id,received_at,quantity_received,quantity_remaining,unit_cost,is_sample)
select d.shop_id,b.id,d.id,p.id,(current_date-35)::timestamptz,500,500,p.wholesale_price,true
from public.nexus_dealers d join public.nexus_products p on p.dealer_id=d.id
join public.nexus_branches b on b.branch_code='HK-BR-'||lpad((substring((select shop_code from public.nexus_shops where id=d.shop_id) from 8))::int::text,3,'0')
on conflict do nothing;

-- Four completed sales per shop per day for the last 30 days = 2,400 sales.
with sale_seed as (
 select sno,day_no,slot,
  (current_date-(30-day_no))::date as sale_date,
  (((day_no*4+slot-1)%20)+1) as customer_no,
  ((day_no+slot-2)%10)+1 as dealer_no
 from generate_series(1,20) sno cross join generate_series(1,30) day_no cross join generate_series(1,4) slot
), resolved as (
 select x.*,s.id shop_id,b.id branch_id,c.id customer_id,d.id dealer_id,
  ('HK-SHOP-'||lpad(x.sno::text,3,'0')) shop_code
 from sale_seed x join public.nexus_shops s on s.shop_code='HK-SHOP-'||lpad(x.sno::text,3,'0')
 join public.nexus_branches b on b.branch_code='HK-BR-'||lpad(x.sno::text,3,'0')
 join public.nexus_customers c on c.home_shop_id=s.id and c.pi_username='hk_customer_'||lpad(x.sno::text,3,'0')||'_'||lpad(x.customer_no::int::text,2,'0')
 join public.nexus_dealers d on d.shop_id=s.id and d.dealer_code='HK-DL-'||lpad(x.sno::text,3,'0')||'-'||lpad(x.dealer_no::text,2,'0')
)
insert into public.nexus_sales(receipt_no,shop_id,branch_id,customer_id,dealer_id,subtotal,discount,total,payment_method,payment_status,sold_at,transaction_day,created_by,is_sample)
select 'HK-SALE-'||lpad(sno::text,3,'0')||'-'||lpad(day_no::text,2,'0')||'-'||slot,
 shop_id,branch_id,customer_id,dealer_id,
 round((35+((sno*day_no*slot)%125)+slot*3.75)::numeric,2),
 0,round((35+((sno*day_no*slot)%125)+slot*3.75)::numeric,2),
 (array['Pi','Cash','Card'])[1+((sno+day_no+slot)%3)],'paid',
 (sale_date::timestamp + time '09:00' + (slot-1)*interval '2 hours') at time zone 'Asia/Colombo',
 sale_date,'demo_seed',true
from resolved
on conflict(receipt_no) do nothing;

-- Two real catalogue lines per sample sale; historical unit costs are snapshotted.
insert into public.nexus_sale_items(sale_id,product_id,dealer_id,quantity,unit_price,unit_cost_snapshot,line_total,is_sample)
select sa.id,p.id,p.dealer_id,1,p.retail_price,p.wholesale_price,p.retail_price,true
from public.nexus_sales sa join public.nexus_products p on p.dealer_id=sa.dealer_id
where sa.receipt_no like 'HK-SALE-%' and p.sku in ((select d.dealer_code||'-SKU-01' from public.nexus_dealers d where d.id=sa.dealer_id),(select d.dealer_code||'-SKU-02' from public.nexus_dealers d where d.id=sa.dealer_id))
on conflict do nothing;

-- Reconcile sample receipts to their two item lines and record stock movements.
update public.nexus_sales sa set subtotal=x.line_total,total=x.line_total
from (select sale_id,round(sum(line_total),2) line_total from public.nexus_sale_items group by sale_id) x
where sa.id=x.sale_id and sa.receipt_no like 'HK-SALE-%';

insert into public.nexus_ledger(event_key,event_type,shop_id,branch_id,dealer_id,product_id,quantity_delta,unit_cost,reference_type,reference_id,is_sample)
select 'HK-SALE-STOCK-'||si.id::text,'sale',sa.shop_id,sa.branch_id,si.dealer_id,si.product_id,-si.quantity,si.unit_cost_snapshot,'sale',sa.id,true
from public.nexus_sale_items si join public.nexus_sales sa on sa.id=si.sale_id
where sa.receipt_no like 'HK-SALE-%'
on conflict(event_key) do nothing;

-- 23:50 Sri Lanka time dealer transactions for every sample dealer, every day in 30-day period.
insert into public.nexus_dealer_transactions(transaction_no,dealer_id,shop_id,transaction_date,gross_sold_cost,dealer_fee_rate,dealer_fee,net_payable,scheduled_at,status,is_sample)
select 'HK-DTX-'||d.dealer_code||'-'||to_char(day_date,'YYYYMMDD'),
 d.id,d.shop_id,day_date,
 round(coalesce(sum(si.unit_cost_snapshot*si.quantity),0),2),0.005,
 round(coalesce(sum(si.unit_cost_snapshot*si.quantity),0)*0.005,2),
 round(coalesce(sum(si.unit_cost_snapshot*si.quantity),0)*0.995,2),
 (day_date+time '23:50') at time zone 'Asia/Colombo','processed',true
from public.nexus_dealers d
cross join generate_series(current_date-29,current_date,interval '1 day') day_date
left join public.nexus_sales sa on sa.dealer_id=d.id and sa.transaction_day=day_date::date and sa.payment_status='paid'
left join public.nexus_sale_items si on si.sale_id=sa.id
where d.dealer_code like 'HK-DL-%'
group by d.id,d.dealer_code,d.shop_id,day_date
on conflict(transaction_no) do nothing;

-- Consistent sample dealer settlement mirror for existing settlement UI.
insert into public.nexus_settlements(settlement_no,dealer_id,settlement_date,sold_cost,dealer_fee,net_payable,status,scheduled_at,is_sample)
select 'HK-SET-'||d.dealer_code||'-'||to_char(t.transaction_date,'YYYYMMDD'),
 d.id,t.transaction_date,t.gross_sold_cost,t.dealer_fee,t.net_payable,t.status,t.scheduled_at,true
from public.nexus_dealer_transactions t join public.nexus_dealers d on d.id=t.dealer_id
on conflict(settlement_no) do nothing;

-- Ensure seeded sample records are clearly distinguishable and verify expected volumes.
do $$
declare shop_count int; dealer_count int; product_count int; customer_count int; sale_count int; txn_count int;
begin
 select count(*) into shop_count from public.nexus_shops where shop_code like 'HK-SHOP-%';
 select count(*) into dealer_count from public.nexus_dealers where dealer_code like 'HK-DL-%';
 select count(*) into product_count from public.nexus_products where sku like 'HK-DL-%-SKU-%';
 select count(*) into customer_count from public.nexus_customers where pi_username like 'hk_customer_%';
 select count(*) into sale_count from public.nexus_sales where receipt_no like 'HK-SALE-%';
 select count(*) into txn_count from public.nexus_dealer_transactions where transaction_no like 'HK-DTX-%';
 if shop_count<>20 or dealer_count<>200 or product_count<>2000 or customer_count<>400 or sale_count<>2400 or txn_count<>6000 then
  raise exception 'Seed verification failed: shops %, dealers %, products %, customers %, sales %, dealer transactions %',shop_count,dealer_count,product_count,customer_count,sale_count,txn_count;
 end if;
end $$;
