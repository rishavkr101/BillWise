# main.py
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date
import logging

import crud, models, schemas, parsing
from database import engine, get_db

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Receipt Processor API",
    description="An API to upload, parse, and analyze receipts and bills."
)

# Allow Cross-Origin Resource Sharing (CORS) for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

@app.post("/receipts/upload", response_model=List[schemas.ReceiptResponse], status_code=status.HTTP_201_CREATED)
async def upload_and_process_receipt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint for Data Ingestion and Parsing.
    1. Accepts a file (.jpg, .png, .pdf, .txt).
    2. Processes it to extract raw text using OCR.
    3. Parses the text to find structured data (vendor, date, amount).
    4. Validates the extracted data and stores it in the database.
    """
    # Step 1: Process file content to raw text (handles PDF, JPG, etc.)
    raw_text = await parsing.process_file_to_text(file)
    
    # Log the raw text for debugging (first 200 characters)
    logger.info(f"Raw text extracted: {raw_text[:200]}")
    
    # Step 2: Validate that OCR actually produced text
    if not raw_text or raw_text.isspace():
        logger.warning(f"OCR failed to extract text from file: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Could not extract any text from the file. The file might be empty, corrupted, or an image without text."
        )

    # Step 3: Parse the raw text to get a list of structured receipts
    parsed_receipts = parsing.extract_structured_data(raw_text)
    logger.info(f"Parsed {len(parsed_receipts)} receipts.")

    # Step 4: Validate that at least one receipt was found
    if not parsed_receipts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse any structured data from the document."
        )

    created_receipts = []
    for receipt_data in parsed_receipts:
        # Step 5: Create ReceiptCreate object for each receipt
        receipt_to_create = schemas.ReceiptCreate(
            vendor=receipt_data["vendor"],
            transaction_date=receipt_data["transaction_date"],
            total_amount=receipt_data["total_amount"],
            category=receipt_data.get("category", "Uncategorized"),
            raw_text=receipt_data.get("raw_text", ""),
            original_filename=file.filename
        )
        
        # Step 6: Pass to CRUD layer and collect the result
        created_receipt = crud.create_receipt(db=db, receipt=receipt_to_create)
        created_receipts.append(created_receipt)

    return created_receipts


@app.get("/receipts", response_model=List[schemas.ReceiptResponse])
def get_all_receipts(
    skip: int = 0,
    limit: int = 20,
    sort_by: str = Query("transaction_date", enum=["id", "vendor", "transaction_date", "total_amount"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: Session = Depends(get_db)
):
    """
    Retrieves a paginated and sorted list of all receipts.
    Implements the Sorting Algorithm requirement.
    """
    receipts = crud.get_receipts(db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order)
    return receipts


@app.delete("/receipts/{receipt_id}", response_model=schemas.ReceiptResponse)
def delete_receipt_by_id(receipt_id: int, db: Session = Depends(get_db)):
    db_receipt = crud.get_receipt_by_id(db, receipt_id=receipt_id)
    if db_receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    crud.delete_receipt(db=db, receipt_id=receipt_id)
    return db_receipt

@app.get("/receipts/search", response_model=List[schemas.ReceiptResponse])
def search_for_receipts(
    keyword: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """

    Searches receipts by keyword (in vendor) and/or a date range.
    Implements the Search Algorithm requirement.
    """
    if not any([keyword, start_date, end_date]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide at least one search parameter.")
    
    receipts = crud.search_receipts(db, keyword=keyword, start_date=start_date, end_date=end_date)
    return receipts

@app.get("/receipts/summary", response_model=schemas.AggregationSummary)
def get_expenditure_summary(db: Session = Depends(get_db)):
    """
    Provides aggregated statistics about all receipts.
    Implements the Aggregation Functions requirement.
    """
    summary = crud.get_aggregation_summary(db)
    return summary

@app.get("/receipts/statistics", response_model=Dict[str, float])
def get_expense_statistics(db: Session = Depends(get_db)):
    """
    Returns statistics on expenses: sum, mean, median, mode
    """
    return crud.get_expense_statistics(db=db)

@app.get("/receipts/vendor-frequencies", response_model=Dict[str, int])
def get_vendor_frequencies(db: Session = Depends(get_db)):
    """
    Returns frequency counts for each vendor
    """
    return crud.get_vendor_frequencies(db=db)

@app.get("/receipts/monthly-spend", response_model=Dict[str, float])
def get_monthly_spend(db: Session = Depends(get_db)):
    """
    Returns monthly total spend
    """
    return crud.get_monthly_spend(db=db)

@app.get("/receipts/export-csv")
def export_receipts_csv(db: Session = Depends(get_db)):
    """
    Exports all receipts as CSV
    """
    receipts = crud.get_receipts(db, skip=0, limit=1000000)
    
    # Create CSV content
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["id", "vendor", "transaction_date", "total_amount", "category", "raw_text", "original_filename"])
    
    # Write rows
    for receipt in receipts:
        writer.writerow([
            receipt.id,
            receipt.vendor,
            receipt.transaction_date,
            receipt.total_amount,
            receipt.category,
            receipt.raw_text,
            receipt.original_filename
        ])
    
    # Return as downloadable file
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=receipts_export.csv"}
    )

@app.get("/receipts/export-json")
def export_receipts_json(db: Session = Depends(get_db)):
    """
    Exports all receipts as JSON
    """
    receipts = crud.get_receipts(db, skip=0, limit=1000000)
    
    # Convert to list of dictionaries
    receipts_dict = [
        {
            "id": r.id,
            "vendor": r.vendor,
            "transaction_date": str(r.transaction_date),
            "total_amount": r.total_amount,
            "category": r.category,
            "raw_text": r.raw_text,
            "original_filename": r.original_filename
        }
        for r in receipts
    ]
    
    # Return as downloadable file
    return JSONResponse(
        content=receipts_dict,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=receipts_export.json"}
    )