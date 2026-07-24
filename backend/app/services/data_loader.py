import json
from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_and_profile(file_path: str) -> dict:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    rows, columns = df.shape
    sample = json.loads(df.head(5).to_json(orient="records"))

    return {
        "shape": {"rows": rows, "columns": columns},
        "columns": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample": sample,
        "null_counts": {col: int(count) for col, count in df.isnull().sum().items()},
    }
