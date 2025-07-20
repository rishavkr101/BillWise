# models.py
from sqlalchemy import Column, Integer, String, Float, Date, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(String, index=True, nullable=False)
    transaction_date = Column(Date, index=True, nullable=False)
    total_amount = Column(Float, index=True, nullable=False)
    category = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    original_filename = Column(String, nullable=True)
    currency = Column(String, default="INR")  # Default to Indian Rupee
    created_at = Column(DateTime(timezone=True), server_default=func.now())
