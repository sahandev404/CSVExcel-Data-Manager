import pandas as pd
import os
import re
from datetime import datetime
import math
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
HEADERS_OUTPUT_DIR = r"C:\New folder\extracted_headers"
LABELS_OUTPUT_FILE = os.path.join(HEADERS_OUTPUT_DIR, "label_info.csv")
os.makedirs(HEADERS_OUTPUT_DIR, exist_ok=True)

# Global variable to store current uploaded file data
current_file = {
    "df": None,
    "filename": None,
    "headers": [],
    "row_count": 0
}


# def normalize_header_text(text: str) -> str:
#     return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


# def classify_age_header(header: str) -> dict[str, str | bool]:
#     text = normalize_header_text(header)

#     # Exclude headers that describe a different group's age or an entity's age.
#     negative_pattern = re.compile(
#         r"\b(age(?:\s*group)?)(?:\s*of|\s+for|\s+from)?\s+(patients?|children|child|customers?|clients?|employees?|staff|students?|members?|family|household|parents?|spouses?|partners?|patients?)\b"
#         r"|\b(patients?|children|child|customers?|clients?|employees?|staff|students?|members?|family|household|parents?|spouses?|partners?)\b.*\b(age(?:\s*group)?|years old|how old|current age|age range)\b"
#     )
#     if negative_pattern.search(text):
#         return {
#             "label": "Not Age",
#             "reason": "References another group or entity rather than the data owner/respondent"
#         }

#     # Positive signals for age labels.
#     age_positive = re.compile(
#         r"\b(current age|your age|my age|respondent(?:'s)? age|participant(?:'s)? age|subject(?:'s)? age|owner(?:'s)? age|age range|age(?: \(years\)| in years)?|years old|how old|age)\b"
#     )
#     if not age_positive.search(text):
#         return {"label": "Not Age", "reason": "No direct age-related wording found"}

#     # If the header explicitly refers to self/respondent/or owner, accept as Age.
#     self_signal = re.compile(r"\b(your|you|current|my|respondent|participant|subject|owner|self)\b")
#     if self_signal.search(text):
#         return {"label": "Age", "reason": "Direct self/owner age reference found"}

#     # If it contains an age group or age range with no clear unrelated entity, accept as Age.
#     if re.search(r"\b(age group|age range|years old|how old|current age|age \(years\)|age in years)\b", text):
#         return {"label": "Age", "reason": "Age-related field without unrelated entity context"}

#     return {"label": "Not Age", "reason": "Age wording appears ambiguous or not directly about the owner/respondent"}

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
    existing_headers = {
        str(value).strip()
        for value in existing_df.loc[
            existing_df["file name"].astype(str).str.strip() == str(filename).strip(),
            "header text"
        ].dropna().tolist()
    }

    new_rows = []
    for index, header in enumerate(headers):
        header_text = "" if pd.isna(header) else str(header)
        normalized_header = header_text.strip()
        if normalized_header in existing_headers:
            continue

        label_info = classify_age_header(header_text)
        new_rows.append({
            "Label": label_info["label"],
            "header text": header_text,
            "file name": filename,
            "header index": index,
        })
        existing_headers.add(normalized_header)

    if not new_rows:
        return {
            "success": True,
            "message": "No new headers to record",
            "rows_added": 0,
            "output_file": os.path.basename(LABELS_OUTPUT_FILE),
        }

    combined_df = pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
    combined_df = combined_df[columns]
    combined_df.to_csv(LABELS_OUTPUT_FILE, index=False)

    return {
        "success": True,
        "message": "Label metadata recorded successfully",
        "rows_added": len(new_rows),
        "output_file": os.path.basename(LABELS_OUTPUT_FILE),
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