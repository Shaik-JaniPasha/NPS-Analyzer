from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid

# ✅ Import processing logic
from backend.nps_tool import process_nps

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- FOLDERS ----------------
INPUT_DIR = "input_files"
OUTPUT_DIR = "output_files"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ✅ Serve output files (Download fix)
app.mount("/output_files", StaticFiles(directory=OUTPUT_DIR), name="output_files")

# ---------------- HEALTH CHECK ----------------
@app.get("/")
def home():
    return {"status": "NPS Analyzer Backend Running 🚀"}

# ---------------- UPLOAD API ----------------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Only Excel files allowed")

        # Unique filename (prevents overwrite + caching issues)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        input_path = os.path.join(INPUT_DIR, unique_name)

        # Save uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"📂 File received: {file.filename}")

        # Process file
        output_file, kpi, focus_areas, insights = process_nps(input_path)

        print(f"✅ Processing completed")

        # Validate output file exists
        if not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="Output file not generated")

        return {
            "message": "Processing complete",
            "download_url": f"/output_files/{os.path.basename(output_file)}",
            "kpi": kpi,
            "focus_areas": focus_areas,
            "insights": insights
        }

    except HTTPException as he:
        raise he

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- DOWNLOAD API (SAFE) ----------------
@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)