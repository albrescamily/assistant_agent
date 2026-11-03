import csv
from pathlib import Path

from clients.embedding import embed
from sources.policies import chunk_policies
from sources.products import read_products

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "generated"


def save_csv(path, rows, vectors):
    columns = [key for key in rows[0] if key != "text"]  # every other field is a database column

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns + ["embedding"])  # must match the column list in db/05-vector-load.sql
        for row, vector in zip(rows, vectors, strict=True):  # strict: fails if the server returned fewer vectors
            writer.writerow([row[column] for column in columns] + [str(vector)])  # "[0.1, -0.2, ...]" is pgvector's text format


if __name__ == "__main__":
    chunks = chunk_policies()
    vectors = embed([chunk["text"] for chunk in chunks])
    save_csv(OUTPUT_DIR / "policy_chunks.csv", chunks, vectors)
    print(f"{len(chunks)} chunks written")

    products = read_products()
    vectors = embed([product["text"] for product in products])
    save_csv(OUTPUT_DIR / "product_embeddings.csv", products, vectors)
    print(f"{len(products)} products written")