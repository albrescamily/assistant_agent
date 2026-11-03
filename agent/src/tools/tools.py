from tools.db_connection import connect


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


#Tool Registry
FUNCTIONS = {
    "get_orders": get_orders,
}
