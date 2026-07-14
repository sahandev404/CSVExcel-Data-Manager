import pandas as pd
import os
import re
from datetime import datetime
import math
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from file_service import persist_label_info, build_label_info, read_label_info, make_json_safe, persist_manual_label_text
from file_service import HEADERS_OUTPUT_DIR
from file_service import current_file

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    label_info = build_label_info(header, filename=current_file["filename"], header_index=current_file["headers"].index(header))
    return {
        "header": header,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "rows": safe_records,
        "label_info": label_info
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