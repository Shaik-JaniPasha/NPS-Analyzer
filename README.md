# NPS Final

NPS Final is a FastAPI + React application for analyzing NPS survey exports with a focus on manager-ready reporting.

It processes the NPS score from `SA Question 4`, reads free-text customer feedback from `SA Question 6`, translates that comment into English, classifies the feedback into actionable service themes, separates passive and detractor focus areas, and generates a downloadable Excel workbook with summaries.

## What it does

- Maps NPS scores into:
  - `Detractor`: `0-6`
  - `Passive`: `7-8`
  - `Promoter`: `9-10`
- Translates only the `SA Question 6` comment field
- Splits feedback into service-focused themes such as:
  - `Pricing and Offer Competitiveness`
  - `Cancellation and Retention Handling`
  - `Agent Courtesy and Empathy`
  - `Resolution Quality and Ownership`
  - `Agent Knowledge and Accuracy`
  - `Language and Communication`
  - `Response Time and Wait Time`
  - `Chat and Bot Experience`
  - `Technical Product or Device Issue`
  - `Contact Channel Preference`
  - `Process and Policy Friction`
  - `Survey without comment`
- Calculates avoidable vs non-avoidable impact only for `Passives` and `Detractors`
- Excludes `Promoters` from avoidable impact analysis by marking them as `Not Applicable`
- Labels blank comments as `No Feedback written by customer`

## Current UX

- Drag-and-drop Excel upload
- Live processing progress
- KPI cards for response mix and NPS score
- Interactive focus-area chart for `Detractor` and `Passive` themes
- Separate avoidable impact breakdown for passive and detractor surveys
- Downloadable processed workbook

## Project structure

- `backend/app.py`: FastAPI app, upload endpoint, progress polling, download endpoint
- `backend/nps_tool.py`: NPS score mapping, translation, theme classification, avoidable-impact rules, workbook export
- `frontend/src/App.jsx`: main React UI and reporting dashboard
- `frontend/src/index.css`: dashboard styling
- `frontend/index.html`: app shell metadata

## Local setup

### Backend

```powershell
cd C:\Users\shaikjan\Documents\NPS_Final
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd C:\Users\shaikjan\Documents\NPS_Final\frontend
$env:VITE_API_BASE_URL="http://localhost:8000"
npm install
npm run dev
```

Open `http://localhost:5173/`.

## How to test

1. Start backend and frontend.
2. Upload an Excel workbook containing `SA Question 4` and `SA Question 6`.
3. Confirm:
   - German comments in `SA Question 6` are translated into English
   - blank comments become `No Feedback written by customer`
   - blank-comment rows are grouped under `Survey without comment`
   - focus areas can be toggled between `Detractor` and `Passive`
   - avoidable impact is shown separately for `Detractor Surveys` and `Passive Surveys`
   - promoters do not appear in avoidable-impact reporting
4. Download the generated workbook and review the sheets:
   - `Detailed Data`
   - `Summary`
   - `Focus Areas`
   - `Avoidable Impact`
   - `KPIs`
   - `Synopsis`

## API overview

- `POST /api/upload`
  - accepts an Excel file upload
  - starts processing in the background
  - returns a `job_id`
- `GET /api/progress/{job_id}`
  - returns job progress and final result payload
- `GET /api/download/{filename}`
  - downloads the generated output workbook

## Deployment

The app is now set up so the backend can serve the built React frontend from `backend/static`.

- Build output is generated from `frontend/` into `backend/static`
- The FastAPI app serves:
  - `/api/*` for backend endpoints
  - `/output_files/*` for generated workbook downloads
  - `/` for the React frontend

To create a production frontend build locally:

```powershell
cd C:\Users\shaikjan\Documents\NPS_Final\frontend
npm run build
```

If your Render service is connected to the GitHub repository and deploys from `main`, pushing `main` should update the live app at the existing Render URL.

For a Render-only deployment, use:

- Build command:
  `pip install -r backend/requirements.txt`
- Start command:
  `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
- Root directory:
  repository root

This repository also includes [render.yaml](C:\Users\shaikjan\Documents\NPS_Final\render.yaml) with the same configuration so the service can be recreated as a Render Blueprint if needed.

## Notes

- Translation is limited to `SA Question 6` by design.
- Translation quality is improved with a layered fallback pipeline, but it is still rule-assisted rather than a full dedicated translation engine.
- Generated files in `input_files/`, `output_files/`, `frontend/dist/`, and `__pycache__/` are runtime artifacts and usually should not be committed.
