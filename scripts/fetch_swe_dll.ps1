param(
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $PSScriptRoot "..\\vendor\\swe"
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$zipPath = Join-Path $OutDir "sweph.zip"
$dllPath = Join-Path $OutDir "swedll64.dll"

if (Test-Path $dllPath) {
  Write-Host "Updating existing DLL: $dllPath"
  Remove-Item -Path $dllPath -Force
}

$url = "https://raw.githubusercontent.com/aloistr/swisseph/master/windows/sweph.zip"
Write-Host "Downloading Swiss Ephemeris Windows package from $url"
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting to $OutDir"
Expand-Archive -Path $zipPath -DestinationPath $OutDir -Force

if (-not (Test-Path $dllPath)) {
  # Preferred location inside the archive.
  $preferred = Join-Path $OutDir "sweph\\bin\\swedll64.dll"
  if (Test-Path $preferred) {
    Copy-Item -Force -Path $preferred -Destination $dllPath
  }
}

if (-not (Test-Path $dllPath)) {
  # Fallback: first DLL we can find.
  $found = Get-ChildItem -Path $OutDir -Filter "*.dll" -Recurse | Select-Object -First 1
  if ($null -eq $found) {
    throw "No DLL found after extracting $zipPath"
  }
  Copy-Item -Force -Path $found.FullName -Destination $dllPath
}

Write-Host "Ready: $dllPath"
