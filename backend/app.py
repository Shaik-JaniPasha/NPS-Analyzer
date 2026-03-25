from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import pandas as pd
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
from pathlib import Path
from pathlib import Path

from nps_tool import *

app = FastAPI()
app.mount("/output_files", StaticFiles(directory="output_files"), name="output_files")

# If a built frontend exists, serve it at the root (so landing page shows the app)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # Mount built assets under /static to avoid catching API POST requests.
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend_static")

    # Serve index.html at root for browser access (GET only).
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        @app.get("/")
        def serve_index():
            return FileResponse(str(index_file), media_type='text/html')


@app.get('/plain')
def plain_html():
    """Serve a simple plain-HTML landing page for manual testing (no React required)."""
    plain = Path(__file__).resolve().parent.parent / "frontend" / "plain_index.html"
    if plain.exists():
        return FileResponse(str(plain), media_type='text/html')
    raise HTTPException(status_code=404, detail='plain_index.html not found')

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "input_files"
OUTPUT_FOLDER = "output_files"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    input_path = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save file
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run your processing logic
    output_file = process_nps(input_path)   # 👈 IMPORTANT

    # Load output to extract insights
    df = pd.read_excel(output_file, sheet_name="KPIs")
    kpis = dict(zip(df["Metric"], df["Value"]))

    focus_df = pd.read_excel(output_file, sheet_name="Focus Areas")
    focus_areas = focus_df.to_dict(orient="records")

    insights_df = pd.read_excel(output_file, sheet_name="Key Insights")
    insights = insights_df["Insights"].tolist()

    return {
        "kpis": kpis,
        "focus_areas": focus_areas,
        "insights": insights,
        "download_file": output_file
    }