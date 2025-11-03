# alert_test.ps1 - helpers to simulate alert conditions for HeyAnon
# Usage: run from infra/ in PowerShell

param(
    [switch]$SendSyntheticAlert,
    [switch]$SpamErrors,
    [string]$AlertmanagerUrl = 'http://localhost:9093/api/v1/alerts'
)

function Send-SyntheticAlert($name, $labels, $annotations) {
    $payload = @([
        @{labels = $labels; annotations = $annotations; startsAt = (Get-Date).ToString("o")} 
    ]) | ConvertTo-Json -Depth 6
    Write-Host "Posting synthetic alert $name to $AlertmanagerUrl"
    iwr -Method Post -Uri $AlertmanagerUrl -ContentType 'application/json' -Body $payload -TimeoutSec 5
}

if ($SendSyntheticAlert) {
    Send-SyntheticAlert -name 'SyntheticCopyError' -labels @{alertname='SyntheticCopyError'; severity='warning'; strategyId='mtf-btc-1h-6h-16h'} -annotations @{summary='Synthetic copy error for testing'; description='Triggered by infra/alert_test.ps1'}
    Write-Host "Synthetic alert sent. Check Alertmanager/Discord relay.";
}

if ($SpamErrors) {
    Write-Host "Spamming 200 requests including some invalid payloads to generate 5xx errors..."
    for ($i=0; $i -lt 200; $i++) {
        try {
            # some invalid posts to cause 4xx/5xx depending on API logic
            $body = @{ strategyId = 'test'; orderId = "bad-$i"; ts = (Get-Date).ToString('o'); type = 'market' } | ConvertTo-Json
            iwr -Method Post -Uri 'http://localhost:8000/v1/events/trade' -Body $body -ContentType 'application/json' -TimeoutSec 2
        } catch {
            # ignore
        }
    }
    Write-Host "Spam completed. Wait a minute and check Prometheus for error-rate alerts.";
}

Write-Host "To test stale heartbeat: stop the bot container (docker compose stop bot), wait ~3 minutes, then check Prometheus/Alertmanager." 
