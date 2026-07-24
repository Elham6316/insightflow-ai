import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import Dataset
from app.db.session import get_db
from app.services.data_loader import load_and_profile

router = APIRouter()

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


@router.post("/upload")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / saved_filename

    with open(file_path, "wb") as out:
        out.write(await file.read())

    profile = load_and_profile(str(file_path))

    dataset = Dataset(
        filename=file.filename,
        file_path=str(file_path),
        row_count=profile["shape"]["rows"],
        col_count=profile["shape"]["columns"],
        status="uploaded",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {"dataset_id": str(dataset.id), "profile": profile}
