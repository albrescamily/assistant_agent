COPY policy_chunks (section, content, embedding) FROM '/data/generated/policy_chunks.csv' WITH (FORMAT csv, HEADER true);
COPY product_embeddings (product_id, embedding) FROM '/data/generated/product_embeddings.csv' WITH (FORMAT csv, HEADER true);
