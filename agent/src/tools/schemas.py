from pydantic import BaseModel, Field


# The docstring becomes the tool description the model reads, and each Field description goes into the parameters schema
class GetOrdersInput(BaseModel):
    """Look up one of the customer's orders by email and order number. Use it when the customer asks about an order's status, tracking code, total or delivery date. If the customer hasn't given both the email and the order number, ask for the missing one before calling."""

    email: str = Field(description="The email the customer used to buy, exactly as they typed it.")
    order_id: int = Field(gt=0, description="The order number, e.g. 102. Digits only, without '#' or other text.")
