# deploy-and-verify.ps1
#
# Pushes the ADMIN_PASSPHRASE revert, redeploys startup-kit-app to Cloud Run with the
# correct, permanent security posture (real Google IAM auth via --no-allow-unauthenticated,
# since this org's iam.allowedPolicyMemberDomains policy makes --allow-unauthenticated
# unusable), confirms access, and launches the authenticated proxy for manual verification.
#
# Run from the repo root: C:\Users\james\PycharmProjects\PythonProject\Startup_Kit
# Requires: gcloud authenticated as an account with run.invoker on this service,
# env-vars.yaml present in the repo root (gitignored, local-only).

$ErrorActionPreference = "Stop"

function Step($message) {
    Write-Host ""
    Write-Host "=== $message ===" -ForegroundColor Cyan
}

Step "1. Push the ADMIN_PASSPHRASE revert"
git push origin main
if ($LASTEXITCODE -ne 0) { throw "git push failed -- resolve before continuing." }

Step "2. Confirm env-vars.yaml exists"
if (-not (Test-Path "env-vars.yaml")) {
    throw "env-vars.yaml not found in the current directory. Create it first (see docs/Cloud_Run_Deployment.md Section 6) before deploying."
}
Get-Content "env-vars.yaml"

Step "3. Deploy to Cloud Run (real IAM auth, no public access)"
gcloud run deploy startup-kit-app `
    --source . `
    --region us-east1 `
    --service-account cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com `
    --env-vars-file env-vars.yaml `
    --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest `
    --set-secrets ADMIN_PASSPHRASE=admin-passphrase:latest `
    --timeout=1800 `
    --min-instances=1 `
    --no-allow-unauthenticated
if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed -- see the error above before continuing." }

Step "4. Confirm who currently has run.invoker on this service"
gcloud run services get-iam-policy startup-kit-app --region us-east1

Step "5. Launch the authenticated proxy for manual verification"
Write-Host "Once the proxy starts, open the printed http://127.0.0.1:PORT URL in your browser" -ForegroundColor Yellow
Write-Host "and run a real Generate -> Fact Review -> Approve -> Generate documents cycle." -ForegroundColor Yellow
Write-Host "Press Ctrl+C in this window when you're done verifying to stop the proxy." -ForegroundColor Yellow
Write-Host ""
gcloud run services proxy startup-kit-app --region us-east1 --project toptal-delivery-apps
