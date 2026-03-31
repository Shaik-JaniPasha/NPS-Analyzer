from __future__ import annotations

import os
import shutil
import uuid
from threading import Lock

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.nps_tool import process_nps

app = FastAPI(title="NPS Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_DIR = "input_files"
OUTPUT_DIR = "output_files"
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

progress_store: dict[str, dict] = {}
progress_lock = Lock()

app.mount("/output_files", StaticFiles(directory=OUTPUT_DIR), name="output_files")


def update_job(job_id: str, **updates):
    with progress_lock:
        current = progress_store.get(job_id, {})
        progress_store[job_id] = {**current, **updates}


def process_job(job_id: str, input_path: str):
    try:
        update_job(job_id, status="processing", message="Analyzing uploaded feedback")

        def update_progress(current: int, total: int):
            percent = int((current / total) * 100) if total else 0
            update_job(
                job_id,
                current=current,
                total=total,
                percent=percent,
                status="processing",
                message="Processing response themes and sentiment",
            )

        result = process_nps(input_path, progress_callback=update_progress)
        output_file = result["output_file"]
        if not os.path.exists(output_file):
            raise FileNotFoundError("Output file was not generated.")

        update_job(
            job_id,
            status="completed",
            percent=100,
            message="Analysis complete",
            result={
                "message": "Processing complete",
                "download_url": f"/output_files/{os.path.basename(output_file)}",
                "download_filename": os.path.basename(output_file),
                "kpi": result["kpi"],
                "summary": result["summary"],
                "focus_areas": result["focus_areas"],
                "avoidable_summary": result["avoidable_summary"],
                "insights": result["insights"],
            },
        )
    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            error=str(exc),
            message="Processing failed",
        )


@app.get("/")
def home():
    return {"status": "NPS Analyzer Backend Running"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/upload", status_code=202)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed.")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large. Please upload a file under 15 MB.")

    job_id = str(uuid.uuid4())
    safe_name = os.path.basename(file.filename)
    unique_name = f"{job_id}_{safe_name}"
    input_path = os.path.join(INPUT_DIR, unique_name)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    update_job(
        job_id,
        status="queued",
        current=0,
        total=1,
        percent=0,
        filename=safe_name,
        message="Upload received",
    )
    background_tasks.add_task(process_job, job_id, input_path)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Upload successful. Processing has started.",
    }


@app.get("/api/progress/{job_id}")
def get_progress(job_id: str):
    job = progress_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path, filename=safe_name)
