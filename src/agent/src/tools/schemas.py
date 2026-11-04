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


class SearchProductsInput(BaseModel):
    """Search the store's catalog. Use it for any product question: what the store has, the price of a model, options within a budget, or recommendations like 'violão para iniciante'. Never state a product, price or stock that didn't come from this tool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="What the customer wants, as a short phrase in Portuguese. Keep brand and model names as written, e.g. 'Takamine GD20'.")
    category: Literal["Guitarras", "Baixos", "Baterias e Percussão", "Teclados e Pianos", "Violões",
                      "Instrumentos de Sopro (Madeiras)", "Instrumentos de Sopro (Metais)",
                      "Cordas Orquestrais", "Ukuleles"] | None = Field(default=None, description="Only if the request clearly fits one category.")
    max_price: float | None = Field(default=None, gt=0, description="Maximum price in BRL, only if the customer gave a budget.")


class CheckProductInput(BaseModel):
    """Get everything about a specific product in one call: if it can be bought right now (status, units in stock), its price with any active promotion already applied (final_price_brl), and its details (color, strings, wood, electronics). Use it when the customer names a product and asks about its availability, price, discount or details. It also finds products that are coming soon or discontinued."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, description="Brand and model of the product, without the instrument type, e.g. 'Yamaha C40' or 'Kala Barítono Cedar'.")

