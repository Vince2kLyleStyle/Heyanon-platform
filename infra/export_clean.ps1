param(
  [string]$SourceRoot = ((Resolve-Path "$PSScriptRoot\..\").Path.TrimEnd('\')),
  [string]$OutZip = (Join-Path $PSScriptRoot "heyanon-platform-clean.zip")
)

$ErrorActionPreference = 'Stop'

$temp = Join-Path $env:TEMP ("heyanon-export-" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $temp | Out-Null

Write-Host "[export] Source: $SourceRoot"
Write-Host "[export] Temp:   $temp"

# Copy everything first
Write-Host "[export] Copying project (robocopy) ..."
Write-Host "robocopy `"$SourceRoot`" `"$temp`" *.* /E /R:1 /W:1"
robocopy "$SourceRoot" "$temp" *.* /E /R:1 /W:1 | Out-Host

# Prune heavy/secret items from the temp copy
$pruneDirs = @(
  ".git", "node_modules", ".next", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "bot_data"
)
foreach ($d in $pruneDirs) {
  Get-ChildItem -Path (Join-Path $temp $d) -Directory -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    try { Remove-Item -Recurse -Force -LiteralPath $_.FullName } catch {}
  }
}

# Remove real env files; keep *.example
Get-ChildItem -Path $temp -Recurse -Include ".env", ".env.local" -ErrorAction SilentlyContinue | ForEach-Object { try { Remove-Item -Force $_.FullName } catch {} }

# Remove common compiled/temp files
Get-ChildItem -Path $temp -Recurse -Include "*.pyc","*.pyo","*.log","*.sqlite","*.db" -ErrorAction SilentlyContinue | ForEach-Object { try { Remove-Item -Force $_.FullName } catch {} }

$fileCount = (Get-ChildItem -Path $temp -Recurse -File | Measure-Object).Count
Write-Host "[export] Files staged: $fileCount"

if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
Write-Host "[export] Creating zip: $OutZip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($temp, $OutZip)

if (Test-Path $OutZip) {
  $f = Get-Item $OutZip
  Write-Host ("[export] Done. Zip: {0} ({1} MB)" -f $f.FullName, [math]::Round($f.Length/1MB,2))
} else {
  Write-Warning "[export] Zip not created. Please share the console output so we can fix it."
}