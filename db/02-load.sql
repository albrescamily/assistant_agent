COPY categories FROM '/data/categories.csv' WITH (FORMAT csv, HEADER true);
COPY customers FROM '/data/customers.csv' WITH (FORMAT csv, HEADER true);
COPY products FROM '/data/products.csv' WITH (FORMAT csv, HEADER true);
COPY orders FROM '/data/orders.csv' WITH (FORMAT csv, HEADER true);
COPY order_items FROM '/data/order_items.csv' WITH (FORMAT csv, HEADER true);
COPY promotions FROM '/data/promotions.csv' WITH (FORMAT csv, HEADER true);
