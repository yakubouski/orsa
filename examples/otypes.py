from typing import Optional
from pydantic import BaseModel,Field, model_validator

class OrderItem(BaseModel):
    sku: str
    cost: float
    quantity: Optional[float] = Field(1.0)
    total: Optional[float] = Field(0.0)

    @model_validator(mode="before")
    def calc_total(self):
        self['total'] = self['quantity'] * self['cost']
        return self