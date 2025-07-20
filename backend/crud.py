# crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional, Dict
import statistics

import models
import schemas
from datetime import date

def get_receipt_by_id(db: Session, receipt_id: int):
    return db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()

def create_receipt(db: Session, receipt: schemas.ReceiptCreate):
    db_receipt = models.Receipt(**receipt.model_dump())
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    return db_receipt

def get_receipts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "transaction_date",
    sort_order: str = "desc"
) -> List[models.Receipt]:
    """
    Gets a list of receipts with sorting.
    Time Complexity: O(n log n) due to database sorting on an indexed column.
    """
    sort_column = getattr(models.Receipt, sort_by, models.Receipt.transaction_date)
    order_func = desc if sort_order.lower() == "desc" else asc

    return db.query(models.Receipt).order_by(order_func(sort_column)).offset(skip).limit(limit).all()

def search_receipts(
    db: Session,
    keyword: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[models.Receipt]:
    """
    Performs keyword, range, and pattern-based search.
    - Keyword: Linear scan (O(n)) on the vendor/category fields. Hashed index on vendor improves this.
    - Range: Efficient search (O(log n)) on the indexed date column.
    """
    query = db.query(models.Receipt)
    
    if keyword:
        # Pattern-based search using LIKE
        query = query.filter(models.Receipt.vendor.ilike(f"%{keyword}%"))
    
    if start_date:
        # Range-based search
        query = query.filter(models.Receipt.transaction_date >= start_date)
        
    if end_date:
        query = query.filter(models.Receipt.transaction_date <= end_date)
        
    return query.all()

def get_aggregation_summary(db: Session) -> schemas.AggregationSummary:
    """
    Computes statistical aggregates over the entire dataset.
    """
    receipts = db.query(models.Receipt).all()
    if not receipts:
        return schemas.AggregationSummary(
            total_spend=0, receipt_count=0, average_spend=0, median_spend=0,
            spend_by_vendor={}, spend_over_time={}
        )

    amounts = [r.total_amount for r in receipts]

    # Time-series aggregation (monthly spend)
    monthly_spend_query = db.query(
        func.strftime('%Y-%m', models.Receipt.transaction_date).label('month'),
        func.sum(models.Receipt.total_amount)
    ).group_by('month').order_by('month').all()
    
    spend_over_time = {month: total for month, total in monthly_spend_query}

    # Frequency distribution (spend by vendor)
    vendor_spend_query = db.query(
        models.Receipt.vendor,
        func.sum(models.Receipt.total_amount)
    ).group_by(models.Receipt.vendor).all()

    spend_by_vendor = {vendor: total for vendor, total in vendor_spend_query}

    return schemas.AggregationSummary(
        total_spend=sum(amounts),
        receipt_count=len(amounts),
        average_spend=statistics.mean(amounts),
        median_spend=statistics.median(amounts),
        spend_by_vendor=spend_by_vendor,
        spend_over_time=spend_over_time,
    )

def get_expense_statistics(db: Session) -> Dict[str, float]:
    """
    Calculate various statistics on the receipts' total_amount.
    Returns a dictionary with keys: 'sum', 'mean', 'median', 'mode'.
    """
    # Get all total amounts
    amounts = [receipt.total_amount for receipt in db.query(models.Receipt).all()]
    
    if not amounts:
        return {"sum": 0.0, "mean": 0.0, "median": 0.0, "mode": 0.0}
    
    # Calculate sum
    total = sum(amounts)
    
    # Calculate mean
    mean = total / len(amounts)
    
    # Calculate median
    sorted_amounts = sorted(amounts)
    n = len(sorted_amounts)
    mid = n // 2
    if n % 2 == 0:
        median = (sorted_amounts[mid-1] + sorted_amounts[mid]) / 2
    else:
        median = sorted_amounts[mid]
    
    # Calculate mode
    from statistics import mode
    try:
        mode_val = mode(amounts)
    except statistics.StatisticsError:
        # If there is no unique mode, use the first element
        mode_val = amounts[0] if amounts else 0.0
    
    return {
        "sum": total,
        "mean": mean,
        "median": median,
        "mode": mode_val
    }

def get_vendor_frequencies(db: Session) -> Dict[str, int]:
    """
    Returns a dictionary of vendor names and their occurrence counts
    """
    from collections import defaultdict
    vendor_counts = defaultdict(int)
    receipts = db.query(models.Receipt).all()
    for receipt in receipts:
        vendor_counts[receipt.vendor] += 1
    return dict(vendor_counts)

def get_monthly_spend(db: Session) -> Dict[str, float]:
    """
    Returns monthly total spend as a dictionary of YYYY-MM: amount
    """
    from collections import defaultdict
    from datetime import datetime
    monthly_totals = defaultdict(float)
    receipts = db.query(models.Receipt).all()
    for receipt in receipts:
        if receipt.transaction_date:
            month_key = receipt.transaction_date.strftime("%Y-%m")
            monthly_totals[month_key] += receipt.total_amount
    return dict(monthly_totals)

def delete_receipt(db: Session, receipt_id: int):
    db_receipt = get_receipt_by_id(db, receipt_id)
    if db_receipt:
        db.delete(db_receipt)
        db.commit()
    return db_receipt
