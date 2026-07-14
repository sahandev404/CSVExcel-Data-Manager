import pandas as pd
import os
from classifier import classify_age_header

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

# Tokenizer-based age classification is provided by my_classifire.py.
def make_json_safe(records):
    def safe_value(value):
        if pd.isna(value):
            return None
        return value

    return [
        {key: safe_value(value) for key, value in record.items()}
        for record in records
    ]


def build_label_info(header: str, filename: str | None = None, header_index: int | None = None) -> dict[str, object]:
    """Run the tokenizer-based classifier and return the label payload used by the API."""
    label_info = classify_age_header(header)
    return {
        "label": label_info["label"],
        "reason": label_info["reason"],
        "header_text": str(header).strip(),
        "filename": filename,
        "header_index": header_index,
    }

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
        label_info = build_label_info(header_text, filename=filename, header_index=index)

        matching_rows = (
            (existing_df["file name"] == filename_str)
            & (existing_df["header text"] == normalized_header)
        )

        if matching_rows.any():
            existing_df.loc[matching_rows, "Label"] = str(label_info["label"])
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

    # filename_str = str(filename).strip() if filename else "manual entry"
    filename_str = "manual entry"
    header_text = str(text).strip()
    label_info = build_label_info(header_text, filename=filename_str, header_index=-1)
    matching_rows = (
        (existing_df["file name"] == filename_str)
        & (existing_df["header text"] == header_text)
    )

    if matching_rows.any():
        existing_df.loc[matching_rows, "Label"] = str(label_info["label"])
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