# BillPY - Receipt Processing and Aggregation

BillPY is a full-stack receipt and bill management application that allows users to upload, parse, store, and analyze receipts.

## Features

- Upload receipts in various formats (images, PDFs, text)
- Delete receipts
- Extract structured data using OCR and rule-based parsing
- Store data in SQLite database
- Search, sort, and filter receipts
- Expense statistics (sum, mean, median, mode)
- Vendor frequency distribution
- Monthly spend trend visualization
- Export data as CSV or JSON

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: SQLite
- **Parsing**: pytesseract (OCR), pdfplumber (PDF extraction), regex patterns

## Installation

### Backend

1. Create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the backend:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend

1. Create a virtual environment:
   ```bash
   cd frontend
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the frontend:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Open the frontend at `http://localhost:8501`
2. Use the dashboard to view statistics and visualizations
3. Upload new receipts in the "Upload" tab
4. Browse and search receipts in the "Browse" tab
5. Export data using the buttons in the dashboard

## Project Structure

```
bill-py/
├── backend/             # Backend code
│   ├── crud.py          # Database operations
│   ├── database.py      # Database setup
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   ├── parsing.py       # Receipt parsing logic
│   ├── requirements.txt # Backend dependencies
│   ├── schemas.py       # Pydantic models
│   └── venv/            # Virtual environment
├── frontend/            # Frontend code
│   ├── app.py           # Streamlit application
│   ├── requirements.txt # Frontend dependencies
│   └── venv/            # Virtual environment
└── README.md            # Project documentation
