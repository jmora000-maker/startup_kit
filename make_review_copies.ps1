# Collects the files needed for a snapshot review into review_uploads\
$dest = "review_uploads"
New-Item -ItemType Directory $dest -Force | Out-Null
Remove-Item "$dest\*" -Force -ErrorAction SilentlyContinue

$files = @{
    "arc_approved.json"  = "tests\snapshots\arc_genomics\snapshot.json"
    "arc_proposed.json"  = "tests\snapshots_proposed\arc_genomics\snapshot.json"
    "mock_approved.json" = "tests\snapshots\mock_sow\snapshot.json"
    "mock_proposed.json" = "tests\snapshots_proposed\mock_sow\snapshot.json"
    "rev4_final_report.md" = "reports\rev4_final_report.md"
    "numbered_approved.json" = "tests\snapshots\numbered_deliverables\snapshot.json"
    "numbered_proposed.json" = "tests\snapshots_proposed\numbered_deliverables\snapshot.json"
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
Write-Host "Upload everything in $dest\"