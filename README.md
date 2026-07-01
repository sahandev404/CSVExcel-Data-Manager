# CSVExcel Data Manager

A lightweight CSV/Excel header manager and label classifier with a React frontend and FastAPI backend.

## Features

- Upload CSV or Excel files from the browser
- Persist header classification metadata to `extracted_headers/label_info.csv`
- Automatically classify headers as `Age` or `Not Age`
- Add manual text labels and save them to `label_info.csv`
- View selected column values in a paginated table
- Export header lists as CSV or Excel files

## Repository structure

- `main.py` – FastAPI backend server
- `frontend/` – Vite + React + TypeScript frontend
- `requirements.txt` – Python backend dependencies
- `test_label_csv.py` – backend unit tests for CSV persistence
- `extracted_headers/` – generated output files (ignored in Git)

## Requirements

- Python 3.11+ (or compatible)
- Node.js 20+ and npm

## Backend setup

1. Create and activate a virtual environment (if not already created):

   ```powershell
   python -m venv myEnv
   .\myEnv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Run the backend server:

   ```powershell
   uvicorn main:app --reload
   ```

The backend listens on `http://localhost:8000` by default.

## Frontend setup

1. Install frontend dependencies:

   ```powershell
   cd frontend
   npm install
   ```

2. Run the frontend in development mode:

   ```powershell
   npm run dev
   ```

The frontend will open at `http://localhost:5173` by default.

## Usage

- Upload a CSV or Excel file using the upload section
- The backend will classify headers and save metadata to `extracted_headers/label_info.csv`
- Use the manual text label section to enter custom text and save it to the same CSV file
- Select a header to preview column values and label metadata
- Export header names as CSV or Excel using the export buttons

## Testing

Run backend tests from the repository root:

```powershell
.\myEnv\Scripts\Activate.ps1
python -m unittest test_label_csv.py
```

## Notes for GitHub

- `myEnv/` and generated files are excluded via `.gitignore`
- `extracted_headers/` is ignored because it contains runtime outputs
- Keep `frontend/dist/` and `node_modules/` out of version control

