from tools.db_connection import connect
from clients.embedding import embed


def get_orders(email, order_id):
    with connect() as conn:
        customer = conn.execute(
            "SELECT customer_id FROM customers WHERE lower(email) = lower(%s)",
            (email,),
        ).fetchone()
        if customer is None:
            return {"error": "no customer with this email"}

        order = conn.execute(
            """
            SELECT order_id, order_date, status, total_brl,
                   tracking_code, estimated_delivery
            FROM orders
            WHERE customer_id = %s AND order_id = %s
            """,
            (customer["customer_id"], order_id),
        ).fetchone()
        if order is None:

            return {"error": "order not found for this email"}

        return order

def search_policies(query):
    vector = embed([query])[0]
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT section, content
            FROM policy_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT 4
            """,
            (str(vector),),
        ).fetchall()
    return {"results": rows}


def search_products(query, category=None, max_price=None):
    vector = embed([query])[0]
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT p.product_id, p.name, c.name AS category, p.price_brl, p.stock_quantity, p.description
            FROM product_embeddings e
            JOIN products p ON p.product_id = e.product_id
            JOIN categories c ON c.category_id = p.category_id
            WHERE p.status = 'active'
              AND (%(category)s::text IS NULL OR c.name = %(category)s)
              AND (%(max_price)s::numeric IS NULL OR p.price_brl <= %(max_price)s)
            ORDER BY e.embedding <=> %(vector)s::vector
            LIMIT 5
            """,
            {"vector": str(vector), "category": category, "max_price": max_price},
        ).fetchall()
    return {"results": rows}