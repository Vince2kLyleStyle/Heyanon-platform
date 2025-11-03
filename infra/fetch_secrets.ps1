param(
  [string]$SecretName = 'heyanon/staging',
  [string]$OutFile = '.env.staging',
  [ValidateSet('dotenv','json')][string]$Format = 'dotenv'
)

Write-Host "Fetching secret $SecretName into $OutFile (format=$Format)"

if (-not (Get-Module -ListAvailable -Name AWSPowerShell.NetCore)) {
  Write-Error "AWS PowerShell module 'AWSPowerShell.NetCore' not found. Install-Module -Name AWSPowerShell.NetCore"
  exit 2
}

try {
  $secret = Get-SECSecretValue -SecretId $SecretName -ErrorAction Stop
} catch {
  Write-Error "Failed to fetch secret '$SecretName': $_"
  exit 3
}

$ss = $secret.SecretString
try {
  $hash = ConvertFrom-Json $ss -ErrorAction Stop
} catch {
  Write-Error "Secret string is not valid JSON: $_"
  exit 4
}

if ($Format -eq 'json') {
  $ss | Out-File -FilePath $OutFile -Encoding utf8
  Write-Host "Wrote JSON secret to $OutFile"
  exit 0
}

$lines = $hash.PSObject.Properties | ForEach-Object { "{0}={1}" -f $_.Name, ($_.Value) }
$lines | Out-File -FilePath $OutFile -Encoding utf8
Write-Host "Wrote dotenv file to $OutFile"
