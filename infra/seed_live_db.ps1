<#
    Seeds the live Render database by calling the API /seed endpoint.
    Compatible with Windows PowerShell 5.1.
#>

$ErrorActionPreference = 'Stop'

# Ensure TLS 1.2 for Invoke-RestMethod on older PowerShell
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$apiBase = 'https://heyanon-platform.onrender.com'
Write-Host 'Waiting for API to be ready...'

$maxAttempts = 30
$attempt = 0
$apiReady = $false

while ($attempt -lt $maxAttempts -and -not $apiReady) {
    try {
        $response = Invoke-RestMethod -Uri ("{0}/health" -f $apiBase) -Method Get
        if ($null -ne $response -and $response.ok) {
            $apiReady = $true
            Write-Host 'API is ready.'
        } else {
            throw 'API not ready'
        }
    } catch {
        $attempt++
        Write-Host ('Waiting... ({0}/{1})' -f $attempt, $maxAttempts)
        Start-Sleep -Seconds 10
    }
}

if (-not $apiReady) {
    Write-Host 'API did not become ready in time. Please check Render logs and try again.'
    exit 1
}

Write-Host 'Seeding database...'
try {
    $result = Invoke-RestMethod -Uri ("{0}/seed" -f $apiBase) -Method Post
    $added = if ($result -and $result.PSObject.Properties.Name -contains 'added') { $result.added } else { 'unknown' }
    Write-Host ('Success. Seeded {0} strategies.' -f $added)
    Write-Host 'Everyone can now see strategies at: https://mico-site.onrender.com/strategies'
} catch {
    Write-Host ('Error seeding database: {0}' -f $_)
    Write-Host 'You can try manually at: https://heyanon-platform.onrender.com/docs (use the /seed endpoint)'
}
