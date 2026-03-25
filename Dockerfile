# Multi-stage build: build frontend with node, then build python image to serve via uvicorn

# 1) Build frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
COPY frontend/ .
RUN npm ci --silent && npm run build --silent

# 2) Build backend image and copy built frontend
FROM python:3.11-slim
WORKDIR /app
# system deps for uvicorn and building wheels if needed
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# copy backend
COPY backend/ ./backend/
# copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# install python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
