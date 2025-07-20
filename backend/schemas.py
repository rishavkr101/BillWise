# schemas.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

# Base schema with common fields
class ReceiptBase(BaseModel):
    vendor: str
    transaction_date: date
    total_amount: float
    currency: Optional[str] = "INR"
    category: Optional[str] = None
    original_filename: Optional[str] = None

# Schema for creating a new receipt (includes raw_text)
class ReceiptCreate(ReceiptBase):
    raw_text: str

# Schema for reading/returning a receipt from the API
class ReceiptResponse(ReceiptBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True # Pydantic v2, was orm_mode=True

# Schema for the aggregation/summary endpoint
class AggregationSummary(BaseModel):
    total_spend: float
    receipt_count: int
    average_spend: float
    median_spend: float
    spend_by_vendor: dict
    spend_over_time: dict # e.g., {"2025-07": 1500.50}
