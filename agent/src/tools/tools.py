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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": (
                "Look up one of the customer's orders by email and order number. "
                "Use it when the customer asks about an order's status, tracking code, total or delivery date. "
                "If the customer hasn't given both the email and the order number, ask for the missing one before calling."
            ),
            "parameters": {                  
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The email the customer used to buy, exactly as they typed it.",
                    },
                    "order_id": {
                        "type": "integer",
                        "description": "The order number, e.g. 4. Digits only, without '#' or other text.",
                    },
                },
                "required": ["email", "order_id"],
            },
        },
    },
]

