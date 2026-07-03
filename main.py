import pandas as pd
import os
import re
from datetime import datetime
import math
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create output directory for saved headers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS_OUTPUT_DIR = os.path.join(BASE_DIR, "extracted_headers")
LABELS_OUTPUT_FILE = os.path.join(HEADERS_OUTPUT_DIR, "label_info.csv")
os.makedirs(HEADERS_OUTPUT_DIR, exist_ok=True)

# Global variable to store current uploaded file data
current_file = {
    "df": None,
    "filename": None,
    "headers": [],
    "row_count": 0
}

# ---------- Precompiled patterns (compiled once) ----------

# Any age‑related wording
_AGE_PATTERN = re.compile(
    r"\b(age|years old|how old|current age|age range|age group|age in years)\b"
)

# Self / respondent / owner references
_SELF_PATTERN = re.compile(
    r"\b(your|you|current|my|respondent|participant|subject|owner|self)\b"
)

# ---------- Keyword sets for fast lookup ----------

# Words that clearly refer to a *different* entity (not the respondent/owner)
_EXTERNAL_ENTITIES = {
    "patient", "patients", "child", "children",
    "customer", "customers", "client", "clients",
    "employee", "employees", "staff",
    "student", "students", "member", "members",
    "family", "household",
    "parent", "parents", "spouse", "spouses", "partner", "partners",
    "dog", "dogs", "cat", "cats", "pet", "pets",
    "product", "products", "item", "items",
    "vehicle", "vehicles", "car", "cars",
    "house", "houses", "property", "properties"
}

# Words that just describe the age field itself (modifiers / connectors)
_AGE_MODIFIERS = {
    "group", "range", "years", "old", "limit", "bracket",
    "year", "distribution", "category",
    "and", "or", "by", "to", "from", "in"
}


def normalize_header_text(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def classify_age_header(header: str) -> dict[str, str | bool]:
    """
    Classify a column header as 'Age' (of the respondent/owner) or 'Not Age'.

    The logic is:
      1. Must contain age‑related wording.
      2. If any external entity (patient, dog, product, etc.) appears → Not Age.
      3. If a self‑reference (my, respondent, etc.) appears → Age.
      4. If an age modifier (group, range, and, by, etc.) appears → Age.
      5. Otherwise → default to Age (e.g. plain "Age").
    """
    text = normalize_header_text(header)

    # 1. Must contain age‑related wording
    if not _AGE_PATTERN.search(text):
        return {"label": "Not Age", "reason": "No age‑related wording found"}

    words = set(text.split())

    # 2. External entity takes priority over everything else
    #    (e.g., "age of my dog" → "dog" triggers Not Age)
    if words.intersection(_EXTERNAL_ENTITIES):
        return {
            "label": "Not Age",
            "reason": "Refers to an external entity (e.g., patient, customer, pet, product)"
        }

    # 3. Self / respondent reference → Age
    if _SELF_PATTERN.search(text):
        return {"label": "Age", "reason": "Direct self/owner reference"}

    # 4. Common age‑field modifier → Age
    if words.intersection(_AGE_MODIFIERS):
        return {"label": "Age", "reason": "Age field with common modifier"}

    # 5. Default to Age (covers plain "age", "age (years)", etc.)
    return {"label": "Age", "reason": "General age field"}

def make_json_safe(records):
    def safe_value(value):
        if pd.isna(value):
            return None
        return value

    return [
        {key: safe_value(value) for key, value in record.items()}
        for record in records
    ]

# Persist label metadata for uploaded headers into a CSV file.
def persist_label_info(filename: str, headers: list[str]) -> dict:
    os.makedirs(HEADERS_OUTPUT_DIR, exist_ok=True)
    columns = ["Label", "header text", "file name", "header index"]

    existing_df = pd.DataFrame(columns=columns)
    if os.path.exists(LABELS_OUTPUT_FILE) and os.path.getsize(LABELS_OUTPUT_FILE) > 0:
        try:
            existing_df = pd.read_csv(LABELS_OUTPUT_FILE)
        except pd.errors.EmptyDataError:
            existing_df = pd.DataFrame(columns=columns)

    for col in columns:
        if col not in existing_df.columns:
            existing_df[col] = None

    existing_df = existing_df[columns]
    existing_df["file name"] = existing_df["file name"].astype(str).fillna("").str.strip()
    existing_df["header text"] = existing_df["header text"].astype(str).fillna("").str.strip()
    existing_df["header index"] = pd.to_numeric(existing_df["header index"], errors="coerce")

    rows_added = 0
    rows_updated = 0
    new_rows = []
    filename_str = str(filename).strip()

    for index, header in enumerate(headers):
        header_text = "" if pd.isna(header) else str(header)
        normalized_header = header_text.strip()
        label_info = classify_age_header(header_text)

        matching_rows = (
            (existing_df["file name"] == filename_str)
            & (existing_df["header text"] == normalized_header)
        )

        if matching_rows.any():
            existing_df.loc[matching_rows, "Label"] = label_info["label"]
            existing_df.loc[matching_rows, "header index"] = index
            rows_updated += int(matching_rows.sum())
        else:
            new_rows.append({
                "Label": label_info["label"],
                "header text": header_text,
                "file name": filename,
                "header index": index,
            })
            rows_added += 1

    if rows_added == 0 and rows_updated == 0:
        return {
            "success": True,
            "message": "No new headers to record",
            "rows_added": 0,
            "rows_updated": 0,
            "output_file": os.path.basename(LABELS_OUTPUT_FILE),
        }

    combined_df = pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
    combined_df = combined_df[columns]
    combined_df.to_csv(LABELS_OUTPUT_FILE, index=False)

    return {
        "success": True,
        "message": "Label metadata recorded successfully",
        "rows_added": rows_added,
        "rows_updated": rows_updated,
        "output_file": os.path.basename(LABELS_OUTPUT_FILE),
    }

# Persist label metadata for manually entered text values.
def persist_manual_label_text(text: str, filename: str | None = None) -> dict:
    os.makedirs(HEADERS_OUTPUT_DIR, exist_ok=True)
    columns = ["Label", "header text", "file name", "header index"]

    existing_df = pd.DataFrame(columns=columns)
    if os.path.exists(LABELS_OUTPUT_FILE) and os.path.getsize(LABELS_OUTPUT_FILE) > 0:
        try:
            existing_df = pd.read_csv(LABELS_OUTPUT_FILE)
        except pd.errors.EmptyDataError:
            existing_df = pd.DataFrame(columns=columns)

    for col in columns:
        if col not in existing_df.columns:
            existing_df[col] = None

    existing_df = existing_df[columns]
    existing_df["file name"] = existing_df["file name"].astype(str).fillna("").str.strip()
    existing_df["header text"] = existing_df["header text"].astype(str).fillna("").str.strip()
    existing_df["header index"] = pd.to_numeric(existing_df["header index"], errors="coerce")

    filename_str = str(filename).strip() if filename else "manual entry"
    header_text = str(text).strip()
    label_info = classify_age_header(header_text)
    matching_rows = (
        (existing_df["file name"] == filename_str)
        & (existing_df["header text"] == header_text)
    )

    if matching_rows.any():
        existing_df.loc[matching_rows, "Label"] = label_info["label"]
        existing_df.loc[matching_rows, "header index"] = -1
        rows_updated = int(matching_rows.sum())
        rows_added = 0
        combined_df = existing_df
    else:
        new_row = {
            "Label": label_info["label"],
            "header text": header_text,
            "file name": filename_str,
            "header index": -1,
        }
        combined_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
        rows_added = 1
        rows_updated = 0

    combined_df = combined_df[columns]
    combined_df.to_csv(LABELS_OUTPUT_FILE, index=False)

    return {
        "success": True,
        "message": "Manual label text saved successfully",
        "rows_added": rows_added,
        "rows_updated": rows_updated,
        "output_file": os.path.basename(LABELS_OUTPUT_FILE),
        "label_info": {
            "label": label_info["label"],
            "reason": label_info["reason"],
            "header_text": header_text,
            "filename": filename_str,
            "header_index": -1
        }
    }

# Read label info CSV and return rows plus label options.
def read_label_info(label: str | None = None, filename: str | None = None) -> tuple[pd.DataFrame, list[str], list[str]]:
    columns = ["Label", "header text", "file name", "header index"]
    if not os.path.exists(LABELS_OUTPUT_FILE) or os.path.getsize(LABELS_OUTPUT_FILE) == 0:
        return pd.DataFrame(columns=columns), [], []

    try:
        df = pd.read_csv(LABELS_OUTPUT_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns), [], []

    for col in columns:
        if col not in df.columns:
            df[col] = None

    df = df[columns]
    df["Label"] = df["Label"].astype(str).fillna("").str.strip()
    df["header text"] = df["header text"].astype(str).fillna("").str.strip()
    df["file name"] = df["file name"].astype(str).fillna("").str.strip()
    df["header index"] = pd.to_numeric(df["header index"], errors="coerce").fillna(-1).astype(int)

    all_labels = sorted(df["Label"].dropna().unique().tolist())
    all_files = sorted(df["file name"].dropna().unique().tolist())

    if label:
        df = df[df["Label"] == label]
    if filename:
        df = df[df["file name"] == filename]

    return df, all_labels, all_files

@app.get("/api/labels")
def get_label_info(label: str | None = None, file: str | None = None):
    df, all_labels, all_files = read_label_info(label, file)
    rows = make_json_safe(df.to_dict(orient="records"))
    return {
        "rows": rows,
        "label_options": all_labels,
        "file_options": all_files,
        "selected_label": label or "",
        "selected_file": file or ""
    }

@app.get("/api/labels/export")
def export_label_info(label: str | None = None, file: str | None = None, format: str = "csv"):
    df, _, _ = read_label_info(label, file)
    if df.empty:
        raise HTTPException(status_code=400, detail="No label metadata available for export")

    filename_safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", (label or file or "all")).strip().lower() or "all"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format.lower() in ("excel", "xlsx"):
        output_filename = f"label_info_{filename_safe}_{timestamp}.xlsx"
        output_path = os.path.join(HEADERS_OUTPUT_DIR, output_filename)
        # write Excel using openpyxl engine (ensure openpyxl is installed)
        df.to_excel(output_path, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        output_filename = f"label_info_{filename_safe}_{timestamp}.csv"
        output_path = os.path.join(HEADERS_OUTPUT_DIR, output_filename)
        df.to_csv(output_path, index=False)
        media_type = "text/csv"

    return FileResponse(output_path, filename=output_filename, media_type=media_type)

@app.post("/api/classify-text")
def classify_text(text: dict):
    user_text = str(text.get("text", "")).strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Text is required")

    filename = current_file["filename"] if current_file["filename"] else "manual entry"
    result = persist_manual_label_text(user_text, filename)

    return {
        "success": True,
        "message": "Text classified and saved",
        "label_info": result["label_info"],
        "rows_added": result["rows_added"],
        "rows_updated": result["rows_updated"],
        "output_file": result["output_file"]
    }

@app.get("/api/headers")
def get_headers():
    """Get headers from currently uploaded file"""
    if current_file["df"] is None:
        raise HTTPException(status_code=400, detail="No file uploaded yet")
    return {
        "headers": current_file["headers"]
    }

@app.get("/api/data")
def get_data(header: str | None = None, page: int = 1, page_size: int = 10):
    """Get paginated rows for the selected header from the currently uploaded file"""
    if current_file["df"] is None:
        raise HTTPException(status_code=400, detail="No file uploaded yet")

    if not header:
        raise HTTPException(status_code=400, detail="Header query parameter is required")

    if header not in current_file["headers"]:
        raise HTTPException(status_code=400, detail=f"Header '{header}' not found in uploaded file")

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10

    start = (page - 1) * page_size
    end = start + page_size
    total_records = current_file["row_count"]
    total_pages = max(1, math.ceil(total_records / page_size))

    records = current_file["df"][[header]].iloc[start:end].to_dict(orient="records")
    safe_records = make_json_safe(records)

    label_info = classify_age_header(header)
    return {
        "header": header,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "rows": safe_records,
        "label_info": {
            "label": label_info["label"],
            "reason": label_info["reason"],
            "header_text": header,
            "filename": current_file["filename"],
            "header_index": current_file["headers"].index(header)
        }
    }

@app.post("/api/export-headers")
def export_headers(output_format: str = "csv"):
    """Export headers from currently uploaded file"""
    if current_file["df"] is None:
        raise HTTPException(status_code=400, detail="No file uploaded yet")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(current_file["filename"])[0]
        
        # Create dataframe with headers
        headers_df = pd.DataFrame([current_file["headers"]])
        
        if output_format.lower() == "excel":
            output_filename = f"{base_name}_headers_{timestamp}.xlsx"
            output_path = os.path.join(HEADERS_OUTPUT_DIR, output_filename)
            headers_df.to_excel(output_path, index=False, header=False)
        else:  # default to CSV
            output_filename = f"{base_name}_headers_{timestamp}.csv"
            output_path = os.path.join(HEADERS_OUTPUT_DIR, output_filename)
            headers_df.to_csv(output_path, index=False, header=False)
        
        return {
            "success": True,
            "message": f"Headers exported successfully to {output_format.upper()}",
            "output_file": output_filename,
            "output_path": output_path,
            "output_format": output_format.lower()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting headers: {str(e)}")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload CSV or Excel file and store it for processing.
    
    Args:
        file: CSV or Excel file to upload (.csv, .xlsx, .xls)
    
    Returns:
        JSON with headers and file metadata
    """
    try:
        # Validate filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a valid filename")
        
        # Validate file extension
        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            raise HTTPException(status_code=400, detail="File must be CSV or Excel format (.csv, .xlsx, .xls)")
        
        # Save uploaded file temporarily
        temp_path = f"temp_{datetime.now().timestamp()}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Read file based on extension
            if filename.endswith('.csv'):
                df = pd.read_csv(temp_path)
            else:
                df = pd.read_excel(temp_path)
            
            headers = df.columns.tolist()
            row_count = len(df)
            
            # Store in global variable
            current_file["df"] = df
            current_file["filename"] = file.filename
            current_file["headers"] = headers
            current_file["row_count"] = row_count

            csv_result = persist_label_info(file.filename, headers)
            
            return {
                "success": True,
                "message": "File uploaded successfully",
                "filename": file.filename,
                "headers": headers,
                "header_count": len(headers),
                "row_count": row_count,
                "label_csv": csv_result
            }
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/")
def home():
    return {
        "message": "CSV/Excel Upload API Server",
        "status": "ready for file upload"
    }