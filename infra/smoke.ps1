param(
  [string]$ApiBase = "http://localhost:8000",
  [string]$Auth = "supersecret",
  [string]$Strategy = "mtf-btc-1h-6h-16h"
)

Write-Host "[smoke] Rebuilding targeted bots..."
Push-Location $PSScriptRoot
try {
  docker compose build bot-swing-btc bot-mtf-eth
  docker compose up -d bot-swing-btc bot-mtf-eth | Out-Null
  Start-Sleep -Seconds 5

  $headers = @{ 'Authorization' = "Bearer $Auth"; 'Content-Type' = 'application/json'; 'Idempotency-Key' = [guid]::NewGuid().ToString() }
  $good = '{ "orderId":"tr_smoke_001", "ts":"2025-10-21T17:10:00Z", "symbol":"BTCUSDT", "venue":"binance", "strategyId":"' + $Strategy + '", "side":"buy", "type":"limit", "status":"new", "entryPx":61840.0, "fillPx":61850.25, "qty":0.0125, "fees":0.18, "leverage":1.0, "meta":{"clientOrderId":"mtf-00123"}}'
  $bad  = '{ "strategyId":"' + $Strategy + '", "tradeId":"tr_bad", "symbol":"BTCUSDT", "side":"buy", "qty":"0.0125", "price":"61850.25", "ts":"2025/10/21 17:10" }'

  Write-Host "[smoke] Happy trade =>" -ForegroundColor Cyan
  try { $r = Invoke-RestMethod -Uri "$ApiBase/v1/events/trade" -Method Post -Headers $headers -Body $good; $r | ConvertTo-Json -Compress | Write-Host }
  catch { if ($_.Exception.Response) { $_.Exception.Response.Content.ReadAsStringAsync().Result | Write-Host } else { Write-Warning $_ } }

  Write-Host "[smoke] Duplicate trade =>" -ForegroundColor Cyan
  try { $r2 = Invoke-RestMethod -Uri "$ApiBase/v1/events/trade" -Method Post -Headers $headers -Body $good; $r2 | ConvertTo-Json -Compress | Write-Host }
  catch { if ($_.Exception.Response) { $_.Exception.Response.Content.ReadAsStringAsync().Result | Write-Host } else { Write-Warning $_ } }

  Write-Host "[smoke] Invalid trade =>" -ForegroundColor Cyan
  try { $r3 = Invoke-RestMethod -Uri "$ApiBase/v1/events/trade" -Method Post -Headers $headers -Body $bad -ErrorAction Stop; $r3 | ConvertTo-Json -Compress | Write-Host }
  catch { if ($_.Exception.Response) { "Status: $($_.Exception.Response.StatusCode.value__)" | Write-Host; $_.Exception.Response.Content.ReadAsStringAsync().Result | Write-Host } else { Write-Warning $_ } }

  Write-Host "[smoke] Recent 422s in api logs =>" -ForegroundColor Yellow
  docker compose logs api --tail 200 | Select-String -Pattern ' 422 |Unprocessable|Validation' -CaseSensitive:$false | Select-Object -First 50
}
finally { Pop-Location }
