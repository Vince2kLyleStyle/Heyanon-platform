param(
  [switch]$DryRun,
  [switch]$Strict,
  [string]$SecretsPath = "infra\bot-secrets.json"
)

$StratsFile = "infra\ci\strategies.json"
if (-not (Test-Path $StratsFile)) { Write-Error "Missing $StratsFile"; exit 1 }

$json = Get-Content $StratsFile | ConvertFrom-Json

$services = @{}
$i = 0
function Expand-Placeholders($str) {
  if (-not $str) { return $str }
  return ($str -replace '\$\{([A-Za-z_][A-Za-z0-9_]*)\}', { param($m) (Get-Item -Path Env:\$($m.Groups[1].Value) -ErrorAction SilentlyContinue).Value })
}

foreach ($s in $json) {
  $i++
  $svc = "bot_$i"

  # base environment for every bot
  $envList = @(
    "BASE_URL=http://api:8000",
    "STRATEGY_ID=$s"
  )

  $missingForThis = $false
  if (Test-Path $SecretsPath) {
    $secretsJson = Get-Content $SecretsPath | ConvertFrom-Json
  $botSecret = $secretsJson.$s
  if ($null -ne $botSecret) {
      $sym = if ($botSecret.SYMBOL) { Expand-Placeholders($botSecret.SYMBOL) } else { $null }
      if (-not $sym) { $sym = 'BTC-PERP' }
      $envList += "SYMBOL=$sym"

  $key = if ($botSecret.HEYANON_API_KEY) { Expand-Placeholders($botSecret.HEYANON_API_KEY) } else { $null }
  if (-not $key) { $key = $env:HEYANON_API_KEY }
      if (-not $key) { $missingForThis = $true }
      $envList += "HEYANON_API_KEY=$key"
    } else {
      $envList += "SYMBOL=BTC-PERP"
      if (-not $env:HEYANON_API_KEY) { $missingForThis = $true }
      $envList += "HEYANON_API_KEY=$($env:HEYANON_API_KEY)"
    }
  } else {
    $envList += "SYMBOL=BTC-PERP"
    if (-not $env:HEYANON_API_KEY) { $missingForThis = $true }
    $envList += "HEYANON_API_KEY=$($env:HEYANON_API_KEY)"
  }

  # Print per-strategy diagnostics
  if ($missingForThis) {
    Write-Warning "Missing HEYANON_API_KEY for strategy=$s after fallbacks"
  } else {
    Write-Host "OK: secrets resolved for strategy=$s"
  }

  if ($missingForThis -and $Strict) {
    Write-Error "STRICT mode: aborting due to missing secret for $s"
    exit 10
  }

  $services[$svc] = @{
    build = @{ context = "../bot" }
    container_name = "heyanon_bot_$i"
    environment = $envList
    depends_on = @("api")
    restart = "unless-stopped"
  }
}

$override = @{ version = '3.8'; services = $services }

$tmp = [System.IO.Path]::GetTempFileName()
$tmpYaml = "$tmp.yaml"
$override | ConvertTo-Yaml | Out-File -FilePath $tmpYaml -Encoding utf8

if ($DryRun) { Get-Content $tmpYaml; Remove-Item $tmpYaml; exit 0 }

if ($Strict) { Write-Host "Running in STRICT mode: missing HEYANON_API_KEY will abort the run" }

docker compose -f docker-compose.yml -f $tmpYaml up -d --build
Remove-Item $tmpYaml
Write-Host "Started $i bot(s)"
