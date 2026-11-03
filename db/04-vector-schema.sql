CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE policy_chunks (
    chunk_id SERIAL PRIMARY KEY,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL  -- this must match the dimension of my model
);



CREATE INDEX idx_documents_embedding ON policy_chunks
  USING hnsw (embedding vector_cosine_ops);