<#
.SYNOPSIS
  Opens the AI Transcript Intake Agent process overview in the default browser.
.DESCRIPTION
  Convenience launcher for Overview/process_overview.html. Works regardless of the
  current working directory by resolving the path relative to this script.
#>
$ErrorActionPreference = "Stop"
$doc = Join-Path $PSScriptRoot "process_overview.html"
if (-not (Test-Path $doc)) {
    Write-Error "Overview document not found: $doc"
    exit 1
}
Write-Host "Opening $doc"
Invoke-Item $doc
