import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"  # sources/ -> ingestion/ -> project root
PRODUCTS_PATH = DATA_DIR / "products.csv"
CATEGORIES_PATH = DATA_DIR / "categories.csv"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_products():
    categories = {category["category_id"]: category["name"] for category in read_csv(CATEGORIES_PATH)}

    products = []
    for product in read_csv(PRODUCTS_PATH):
        specs = "; ".join(f"{key}: {value}" for key, value in json.loads(product["specs"]).items())
        products.append({
            "product_id": product["product_id"],
            # only what doesn't change: price, stock and status come from the products table at search time
            "text": f"{product['name']} — {categories[product['category_id']]}\n{product['description']}\n{specs}",
        })
    return products


if __name__ == "__main__":
    for product in read_products():
        print(product["text"], end="\n\n")
