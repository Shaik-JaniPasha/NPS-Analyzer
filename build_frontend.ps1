# Build the React frontend and prepare for serving by backend
# Run this from project root (PowerShell)
Set-Location -Path "$PSScriptRoot"
Write-Output "Building frontend..."
Push-Location frontend
if (-Not (Test-Path node_modules)) {
  npm install
} else {
  Write-Output "node_modules already present; running npm ci is optional."
}
npm run build
Pop-Location
Write-Output "Frontend built at frontend/dist — start backend to serve it."
Write-Output "To run backend locally: uvicorn backend.app:app --reload --port 8000"