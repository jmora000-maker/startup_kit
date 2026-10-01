# promote_snapshots.ps1
# Promotes reviewed snapshots after a human review, with safety checks.
# Usage:
#   .\promote_snapshots.ps1 -Message "Promote snapshots for Rev 6: arc_overextracted, plural citations"
#   .\promote_snapshots.ps1 -Message "..." -Push        (also pushes to origin)

param(
    [Parameter(Mandatory = $true)][string]$Message,
    [switch]$Push
)

$ErrorActionPreference = "Stop"
$spec = "spec\PMO_Startup_Kit_Consolidated_Spec.md"

function Stop-WithError($text) {
    Write-Host "STOPPED: $text" -ForegroundColor Red
    exit 1
}

Write-Host "== 1. Checking the working tree" -ForegroundColor Cyan
$dirty = git status --porcelain | Where-Object { $_ -notmatch "tests/snapshots_proposed/" -and $_ -notmatch "review_uploads/" }
if ($dirty) {
    Write-Host ($dirty -join "`n")
    Stop-WithError "Uncommitted changes other than proposed snapshots. Commit or discard them first."
}

Write-Host "== 2. Making sure the spec is tracked in git" -ForegroundColor Cyan
if (-not (Test-Path $spec)) { Stop-WithError "$spec not found." }
git ls-files --error-unmatch $spec 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    git add $spec
    git commit -m "Track consolidated spec" | Out-Null
    Write-Host "Spec was untracked: now committed."
} else {
    Write-Host "Spec is tracked."
}

Write-Host "== 3. Checking no unapproved changes to oracles" -ForegroundColor Cyan
$oracleChanges = git status --porcelain -- tests/oracles
if ($oracleChanges) { Stop-WithError "Uncommitted changes in tests\oracles. Review them first." }

Write-Host "== 4. Promoting snapshots" -ForegroundColor Cyan
pytest --update-snapshots -q
# Snapshot updates return early, so other failures here are real failures.
if ($LASTEXITCODE -ne 0) { Stop-WithError "pytest --update-snapshots reported failures. Nothing committed." }

Write-Host "== 5. Re-running the full suite (must be 0 failed)" -ForegroundColor Cyan
pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Restoring the previous approved snapshots..." -ForegroundColor Yellow
    git checkout -- tests/snapshots
    git clean -fd tests/snapshots | Out-Null
    Stop-WithError "Tests fail after promotion. Snapshots restored; nothing committed."
}

Write-Host "== 6. Committing" -ForegroundColor Cyan
git add tests/snapshots tests/snapshots_proposed
git commit -m $Message
if ($LASTEXITCODE -ne 0) { Stop-WithError "Commit failed (perhaps nothing changed)." }

if ($Push) {
    Write-Host "== 7. Pushing" -ForegroundColor Cyan
    git push
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Push failed. The commit is saved locally." }
}

Write-Host "DONE." -ForegroundColor Green
git --no-pager log --oneline -3
