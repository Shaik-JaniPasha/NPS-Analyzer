NPS Tool — FastAPI backend + React (Vite) frontend

**Overview**
- **Purpose:** Web-app dto analyze free-text NPS responses in an uploaded Excel file. The backend processes each response (translation → sentiment → theme → avoidable flag), writes a multi-sheet Excel output and returns summary JSON and a downloadable output file.
- **Backend:** FastAPI application in `backend/` exposing `/api/upload` and `/api/download/{filename}` endpoints. Uses an adapted version of the original `nps_tool.py` processing logic in `backend/processor.py`.
- **Frontend:** Small React app (Vite) in `frontend/` with a file upload UI that shows KPIs and a download button. Responsive behavior implemented via CSS media queries and `react-responsive`.

**Repository Layout**
- `nps_tool.py` — original CLI script (kept for reference).
- `backend/` — FastAPI app and processing code:
	- `backend/app.py` — FastAPI app, CORS + session middleware, upload/download endpoints.
	- `backend/processor.py` — core processing logic adapted from `nps_tool.py`.
	- `backend/requirements.txt` — Python dependencies.
- `frontend/` — Vite + React app:
	- `frontend/package.json` — frontend dependencies & scripts.
	- `frontend/index.html`, `frontend/src/*` — React source files.
- `input_files/` — uploads are saved here by the backend.
- `output_files/` — processed Excel outputs are saved here.

**Quick Start (Windows PowerShell)**

1) Backend: create & activate a virtual environment, install dependencies, start server

```powershell
cd C:\Users\shaikjan\Documents\NPS_FINAL
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

# start server (recommended)
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# OR (app.py contains a uvicorn runner):
python backend\app.py
```

2) Frontend: install Node/npm and start dev server

Install Node.js (LTS) or nvm-windows first, then:

```powershell
cd frontend
npm install
npm run dev
```

Frontend dev server defaults to `http://localhost:5173`. The frontend expects the backend at `http://localhost:8000`.

**API Endpoints**
- POST `/api/upload` — upload an Excel file (form field name `file`). Returns JSON with `kpi`, `summary`, `focus_areas`, `avoidable_summary`, and `download_url`.

	Example curl upload (replace path):

	```bash
	curl -v -F "file=@C:/path/to/NPS_Input.xlsx" http://localhost:8000/api/upload
	```

	Successful response JSON example:

	```json
	{
		"status": "ok",
		"kpi": [...],
		"summary": [...],
		"focus_areas": [...],
		"avoidable_summary": [...],
		"download_url": "/api/download/Output_NPS_Input.xlsx",
		"download_filename": "Output_NPS_Input.xlsx"
	}
	```

- GET `/api/download/{filename}` — download a processed Excel file by filename. The backend saves outputs to `output_files/` and serves files only from that directory (path traversal is restricted).

	Example:

	```bash
	curl -O http://localhost:8000/api/download/Output_NPS_Input.xlsx
	```

**Frontend behavior**
- Select an Excel file (`.xlsx` / `.xls`) in the UI and click *Upload & Analyze*.
- The UI will show a processing indicator while the backend runs. When complete it shows a success message and a Download button that uses `download_url` returned by the server.
- If an error occurs the UI will show the error message returned by the backend.

**Processing details (what the backend does)**
- Reads the uploaded Excel using `pandas` and `openpyxl`.
- Selects the 5th column (index 4) by default for NPS/free-text responses; falls back to the last column if a 5th column is not present.
- For each response:
	- Translates to English using `deep_translator.GoogleTranslator` (online; requires network).
	- Computes sentiment polarity via `TextBlob` and labels `Positive`/`Negative`/`Neutral`.
	- Detects simple themes using keyword matching (Delivery Issue, Customer Service, Pricing, Product Quality, Technical Issue, Other).
	- Sets an `Avoidable` vs `Non-Avoidable` flag based on keywords.
- Writes a multi-sheet Excel output with:
	- `Detailed Data` (original data + added columns `Translated_Text`, `Sentiment`, `Theme`, `Avoidable Impact`)
	- `Summary` (group-by Sentiment+Theme)
	- `Focus Areas` (negative responses by Theme)
	- `Avoidable Impact` (counts)
	- `KPIs` (Total, Positive %, Negative %)
	- `Synopsis`

**Dependencies & runtime notes**
- Python packages are listed in `backend/requirements.txt`. Important items:
	- `fastapi`, `uvicorn[standard]` — web server
	- `pandas`, `openpyxl` — Excel I/O
	- `textblob` — sentiment (may need corpora)
	- `deep-translator` — translation (online)
	- `starlette` / `itsdangerous` — session middleware

- If `textblob` raises errors about missing corpora, run:

```powershell
python -m textblob.download_corpora
```

- The backend currently uses `starlette`'s cookie-based `SessionMiddleware` (secret key set in `backend/app.py`). For production, replace with a server-side session store (e.g., Redis) and a proper session backend.

**Security & Production Advice**
- Change the session `secret_key` in `backend/app.py` before deploying.
- Limit `allow_origins` in CORS to your production host(s).
- Consider moving long-running processing to a background worker (Celery/RQ) if you expect large files / high concurrency.
- Use HTTPS in production and secure the download endpoints if outputs contain sensitive data.

**Troubleshooting**
- `uvicorn` not found: ensure you installed inside the activated venv: `python -m pip install -r backend\requirements.txt` and run `python -m uvicorn backend.app:app ...`.
- `npm` not found: install Node.js or nvm-windows and re-run `npm install`.
- Backend import errors (ModuleNotFoundError): install the missing package via `python -m pip install <package>` and re-run the server; common missing package is `itsdangerous` (now included in `requirements.txt`).
- If the frontend hangs on "Processing...": open browser DevTools → Network → inspect the POST `/api/upload` response and check backend uvicorn logs for tracebacks. The frontend will display server error messages when available.

**Quick verification checklist**
1. Start backend: `python -m uvicorn backend.app:app --reload --port 8000`.
2. Start frontend: `cd frontend && npm install && npm run dev`.
3. Open the frontend in browser, upload `input_files/NPS_Input.xlsx`.
4. After success, click Download or call the returned `download_url` to get the processed Excel in `output_files/`.

**Next improvements (suggested)**
- Use Redis or database-backed sessions for scalability and reliability.
- Add file size limits and input validation.
- Replace `deep-translator` and `textblob` with local NLP models if offline processing is required.
- Add unit tests for `backend/processor.py` and CI workflow.

If you want, I can now:
- Add a `Dockerfile` + `docker-compose.yml` to run backend and frontend containers locally, or
- Implement Redis-backed sessions and demonstrate configuration, or
- Add unit tests for `processor.py` and run them here.

Choose one next step and I'll implement it.

Build & Deploy (added)
----------------------

I added automation and containerization helpers so you can build the frontend and produce a single deployable image that serves the app to internet users.

- Build script (Windows PowerShell): `build_frontend.ps1` in the repo root — runs `npm install` (if needed) and `npm run build` inside `frontend/`. The frontend build output is `frontend/dist` which the backend now serves at `/` when present.

- Dockerfile: a multi-stage `Dockerfile` at the repo root that:
	- Builds the frontend with Node.js
	- Copies `frontend/dist` into the Python image
	- Installs backend Python dependencies and runs `uvicorn backend.app:app` on port 8000

Usage examples:

PowerShell (build frontend then run backend locally):
```powershell
./build_frontend.ps1
# then
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Docker (build & run container exposing port 8000):
```powershell
docker build -t nps-tool:latest .
docker run -p 8000:8000 nps-tool:latest
```

Notes:
- `backend/app.py` was updated to mount `frontend/dist` at `/` when the directory exists. This makes the landing page (index.html) available from the backend.
- CORS is currently permissive (`allow_origins=['*']`) for convenience during testing — lock this down for production.
- For cloud deployment, run the Docker image on your provider of choice, or use the same build steps and host `uvicorn` behind a production server (Gunicorn + Uvicorn workers, or ASGI server of your choice) behind HTTPS.

If you'd like, I can add a `docker-compose.yml`, a GitHub Actions workflow to build and push the image, or a short guide to deploy to Render/Fly.io. Which would you prefer?
