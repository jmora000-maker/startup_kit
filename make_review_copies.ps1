# Collects the files needed for a snapshot review into review_uploads\
$dest = "review_uploads"
New-Item -ItemType Directory $dest -Force | Out-Null
Remove-Item "$dest\*" -Force -ErrorAction SilentlyContinue

$files = @{
    "arc_approved.json"       = "tests\snapshots\arc_genomics\snapshot.json"
    "arc_proposed.json"       = "tests\snapshots_proposed\arc_genomics\snapshot.json"
    "mock_approved.json"      = "tests\snapshots\mock_sow\snapshot.json"
    "mock_proposed.json"      = "tests\snapshots_proposed\mock_sow\snapshot.json"
    "nostory_approved.json"   = "tests\snapshots\no_story_ids\snapshot.json"
    "nostory_proposed.json"   = "tests\snapshots_proposed\no_story_ids\snapshot.json"
    "numbered_approved.json"  = "tests\snapshots\numbered_deliverables\snapshot.json"
    "numbered_proposed.json"  = "tests\snapshots_proposed\numbered_deliverables\snapshot.json"
    "overext_approved.json"   = "tests\snapshots\arc_overextracted\snapshot.json"
    "overext_proposed.json"   = "tests\snapshots_proposed\arc_overextracted\snapshot.json"
    "arcapp_approved.json"    = "tests\snapshots\arc_application_implementation\snapshot.json"
    "arcapp_proposed.json"    = "tests\snapshots_proposed\arc_application_implementation\snapshot.json"
}

foreach ($name in $files.Keys) {
    $src = $files[$name]
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination "$dest\$name"
        Write-Host "Copied $src -> $dest\$name"
    } else {
        Write-Host "MISSING: $src" -ForegroundColor Yellow
    }
}

$reportFile = "reports\rev12_final_report.md"
if (Test-Path -LiteralPath $reportFile) {
    Copy-Item -LiteralPath $reportFile "$dest\rev12_final_report.md"
    Write-Host "Copied rev12_final_report.md"
} else {
    Write-Host "MISSING: $reportFile" -ForegroundColor Yellow
}

Write-Host "Upload everything in $dest\"