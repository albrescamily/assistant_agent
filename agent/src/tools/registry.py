from dataclasses import dataclass
from typing import Callable
from pydantic import BaseModel

from tools.schemas import GetOrdersInput, SearchPoliciesInput

from tools.tools import get_orders, search_policies

@dataclass(frozen=True)
class Tool:
    name: str
    input_model: type[BaseModel]
    fn: Callable[..., dict]  # called with the validated fields as keyword arguments

    def spec(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.input_model.__doc__,
            "parameters": self.input_model.model_json_schema(),
        }}

REGISTRY = {t.name: t for t in [
    Tool("get_orders", GetOrdersInput, get_orders),
    Tool("search_policies", SearchPoliciesInput, search_policies)
    
    
    
    ]}


TOOLS = [t.spec() for t in REGISTRY.values()]
