# open-deployed-app.ps1
#
# Opens an authenticated tunnel to the real deployed Cloud Run service (startup-kit-app),
# so you can use it in a browser without remembering the full gcloud command.
#
# Requires: gcloud authenticated as an account with roles/run.invoker on this service.
# Run from anywhere -- this script doesn't depend on the repo location.

Write-Host ""
Write-Host "Connecting to the deployed Startup Kit app..." -ForegroundColor Cyan
Write-Host "Once the proxy starts below, open the printed http://127.0.0.1:PORT URL in your browser." -ForegroundColor Yellow
Write-Host "Leave this window open while you work. Press Ctrl+C here when you're done to disconnect." -ForegroundColor Yellow
Write-Host ""

gcloud run services proxy startup-kit-app --region us-east1 --project toptal-delivery-apps
