<#
.SYNOPSIS
    Rotates the ANTHROPIC_API_KEY secret used by the startup-kit-app Cloud Run service.

.DESCRIPTION
    Adds a new version of the `anthropic-api-key` secret in Secret Manager with a key you
    paste in interactively (never hardcoded, never written to disk or shell history), then
    forces the running Cloud Run service to pick it up by creating a new revision.

.NOTES
    Run this from a shell already authenticated to the correct gcloud project
    (toptal-delivery-apps) -- it does not set or change your active gcloud config.
#>

$ErrorActionPreference = "Stop"

$SecretName = "anthropic-api-key"
$ServiceName = "startup-kit-app"
$Region = "us-east1"

Write-Host "=== Anthropic API key rotation for '$ServiceName' ===" -ForegroundColor Cyan
Write-Host "Secret: $SecretName | Service: $ServiceName | Region: $Region`n"

# --- Step 0: confirm current project context ---
$currentProject = gcloud config get-value project 2>$null
Write-Host "Current gcloud project: $currentProject"
$confirmProject = Read-Host "Proceed with this project? (y/n)"
if ($confirmProject -ne "y") {
    Write-Host "Aborted. Run 'gcloud config set project <project-id>' and try again." -ForegroundColor Yellow
    exit 1
}

# --- Step 1: read the new key securely (not echoed, not saved to history) ---
$secureKey = Read-Host "Paste the new Anthropic API key" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
$plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
# Defensive trim: a stray trailing newline from the paste itself (not just from how we hand
# the value to gcloud below) would otherwise still end up in the secret.
$plainKey = $plainKey.Trim()

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    Write-Host "No key entered. Aborting." -ForegroundColor Red
    exit 1
}

# --- Step 2: add the new secret version ---
# REAL BUG FOUND IN PRODUCTION (HTL-66): piping a string to an external process
# ("$plainKey | gcloud ...") goes through PowerShell's pipe-to-stdin conversion, which can
# append a trailing newline. That caused a real outage -- the API key ended up stored as
# "...KQAA\r\n", and httpcore correctly rejected it as an illegal HTTP header value, which
# surfaced as a generic, misleading "Connection error" with no obvious cause. Writing the
# exact string to a file with no trailing newline, then pointing gcloud at that file, avoids
# the pipe entirely and does not have this problem.
Write-Host "`nAdding new version of secret '$SecretName'..."
$tempFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($tempFile, $plainKey, [System.Text.Encoding]::ASCII)
    gcloud secrets versions add $SecretName --data-file=$tempFile
} finally {
    Remove-Item -Path $tempFile -ErrorAction SilentlyContinue
}

# Clear the plaintext copy from memory as soon as we're done with it
$plainKey = $null
[System.GC]::Collect()

# --- Step 3: confirm the new version landed ---
Write-Host "`nCurrent versions of '$SecretName':"
gcloud secrets versions list $SecretName

# --- Step 4: force Cloud Run to pick up the new secret value ---
# `gcloud run services update` with no actual change flag is a no-op and errors out in
# current gcloud versions -- it needs a real (even if harmless) change to force a new
# revision. A timestamped env var does that without touching any real configuration.
$doRestart = Read-Host "`nForce '$ServiceName' to pick up the new key now? (y/n)"
if ($doRestart -eq "y") {
    Write-Host "Triggering a new revision for '$ServiceName'..."
    $touchValue = Get-Date -Format "yyyyMMddHHmmss"
    gcloud run services update $ServiceName --region $Region --update-env-vars "SECRET_ROTATED_AT=$touchValue"
    # Use ${SecretName} (curly braces), not $SecretName:latest -- PowerShell parses a bare
    # "$Var:text" inside a double-quoted string as a drive-scope reference (like $env:PATH)
    # and silently resolves it to empty instead of "value:text".
    Write-Host "`nDone. The service is now running a new revision that reads '${SecretName}:latest'." -ForegroundColor Green
} else {
    Write-Host "`nSkipped restart. The new secret version is saved, but the running revision" -ForegroundColor Yellow
    Write-Host "won't use it until the next deploy or manual update with a real change flag." -ForegroundColor Yellow
}

Write-Host "`nVerify the new key is actually working by running a real generation through the app --"
Write-Host "there is no direct 'which key is active' readout, so a successful generation is the real confirmation."
