# app/schemas/calculation.py
from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

CalculationType = Literal['addition', 'subtraction', 'multiplication', 'division']


class CalculationBase(BaseModel):
    type: CalculationType = Field(..., description="Operation type")
    inputs: List[float] = Field(..., min_items=2, description="Input values")


class CalculationUpdate(BaseModel):
    type: Optional[CalculationType] = Field(None, description="New operation type")
    inputs: Optional[List[float]] = Field(None, min_items=2, description="New input values")

    @field_validator('inputs')
    @classmethod
    def validate_inputs_for_division(cls, v, info):
        # If inputs provided AND type is division, ensure no zero divisor
        if v is not None:
            t = info.data.get('type')
            if t == 'division' and any(x == 0 for x in v[1:]):
                raise ValueError("Cannot divide by zero.")
        return v


class CalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2: ORM mode

    id: UUID
    user_id: UUID
    type: CalculationType
    inputs: List[float]
    result: Optional[float] = None
    created_at: datetime
    updated_at: datetime

