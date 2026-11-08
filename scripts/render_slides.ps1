$outputDir = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit\exported_pptx_decks\rendered_pngs"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$ppt = New-Object -ComObject PowerPoint.Application

$govDeckPath = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit\exported_pptx_decks\ARC_Governance_Kickoff_Deck\ARC_Application_Implementation_PS_Governance_Kickoff.pptx"
$clientDeckPath = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit\exported_pptx_decks\ARC_Client_Kickoff_Deck\ARC_Application_Implementation_Client_Kickoff_Deck.pptx"

if (Test-Path $govDeckPath) {
    $govPres = $ppt.Presentations.Open($govDeckPath, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse)
    for ($i = 1; $i -le $govPres.Slides.Count; $i++) {
        $slide = $govPres.Slides.Item($i)
        $txt = ""
        foreach ($shp in $slide.Shapes) {
            if ($shp.HasTextFrame -and $shp.TextFrame.HasText) {
                $txt += " " + $shp.TextFrame.TextRange.Text
            }
        }
        if ($txt -match "WHO YOU REPRESENT") {
            $pngPath = Join-Path $outputDir "ARC_Governance_Slide_$($i)_Canonical_Reference_Slide4.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
        if ($txt -match "Deliverable acceptance criteria") {
            $pngPath = Join-Path $outputDir "ARC_Governance_Slide_$($i)_Deliverable_Acceptance_Criteria.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
        if ($txt -match "How milestone acceptance works") {
            $pngPath = Join-Path $outputDir "ARC_Governance_Slide_$($i)_How_Milestone_Acceptance_Works.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
        if ($txt -match "Approach" -and $txt -match "Execution phases") {
            $pngPath = Join-Path $outputDir "ARC_Governance_Slide_$($i)_Approach.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
    }
    $govPres.Close()
}

if (Test-Path $clientDeckPath) {
    $clientPres = $ppt.Presentations.Open($clientDeckPath, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse)
    for ($i = 1; $i -le $clientPres.Slides.Count; $i++) {
        $slide = $clientPres.Slides.Item($i)
        $txt = ""
        foreach ($shp in $slide.Shapes) {
            if ($shp.HasTextFrame -and $shp.TextFrame.HasText) {
                $txt += " " + $shp.TextFrame.TextRange.Text
            }
        }
        if ($txt -match "deliver" -or $txt -match "Deliverables" -or $txt -match "DEL-01") {
            $pngPath = Join-Path $outputDir "ARC_Client_Slide_$($i)_What_We_Will_Deliver.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
        if ($txt -match "Initial risk register" -or $txt -match "RSK-01") {
            $pngPath = Join-Path $outputDir "ARC_Client_Slide_$($i)_Initial_Risk_Register.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
        if ($txt -match "Next steps" -and $txt -match "Owner") {
            $pngPath = Join-Path $outputDir "ARC_Client_Slide_$($i)_Next_Steps.png"
            $slide.Export($pngPath, "PNG", 1920, 1080)
            Write-Host "Rendered: $pngPath"
        }
    }
    $clientPres.Close()
}

$ppt.Quit()
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
