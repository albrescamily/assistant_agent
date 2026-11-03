from typing import Literal

from pydantic import BaseModel, Field,ConfigDict


# The docstring becomes the tool description the model reads, and each Field description goes into the parameters schema
class GetOrdersInput(BaseModel):
    """Look up one of the customer's orders by email and order number. Use it when the customer asks about an order's status, tracking code, total or delivery date. If the customer hasn't given both the email and the order number, ask for the missing one before calling."""

    email: str = Field(description="The email the customer used to buy, exactly as they typed it.")
    order_id: int = Field(gt=0, description="The order number, e.g. 102. Digits only, without '#' or other text.")


class SearchPoliciesInput(BaseModel):
    """Search the store's policy manual: payments, installments, returns, shipping, warranty, privacy and opening hours. Use it whenever the customer asks about a store rule."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(
        min_length=3,
        max_length=200,
        description=(
            "A short, self-contained search phrase in Portuguese describing the rule the customer is asking about. "
            "Rewrite the question in your own words; do not copy greetings, names, emails or order numbers."
        ),
        examples=["prazo para devolução de compra online", "parcelamento no cartão de crédito", "endereço da loja"],
    )


