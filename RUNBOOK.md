# Production Runbook for swing-perp-16h Strategy

**Quick Reference:** What to do when things go wrong

---

## 1. UI Shows "Degraded (retrying)"

**Symptoms:**
- Frontend displays "Degraded" status
- API returning cached data
- Logs showing upstream errors

**Diagnosis:**
```powershell
# Check API logs for errors
docker logs heyanon_api --tail 50 | Select-String "error|500|429"

# Test API health
Invoke-RestMethod http://localhost:8000/health

# Check strategy endpoint
Invoke-RestMethod http://localhost:8000/v1/strategies/swing-perp-16h
```

**Common Causes:**
1. **Upstream rate limiting (429):** CoinGecko API rate limit hit
   - **Fix:** Wait 60s for cache to refresh, or upgrade CoinGecko plan
   - **Prevention:** Increase `SIGNAL_POLL_SECONDS` to 120

2. **Network timeout (5xx):** Slow upstream response
   - **Fix:** Check `COINGECKO_TIMEOUT_SEC` env var (default 20s)
   - **Verify:** `docker exec heyanon_api curl -I https://api.coingecko.com/api/v3/ping`

3. **Cache serving stale data:** Last good state persisting
   - **Check:** `docker exec heyanon_api cat /app/data/strategy_state/swing-perp-16h.json`
   - **OK if:** `lastEvaluated` within last 5 minutes

**Resolution Steps:**
1. Verify API is responding: `curl http://localhost:8000/v1/summary`
2. If 200 OK, frontend will auto-recover on next poll (30s)
3. If 500 errors, restart API: `docker-compose restart api`
4. Check logs again to confirm recovery

---

## 2. Bot Logs Stop Appearing

**Symptoms:**
- `/v1/strategies/swing-perp-16h/logs` returns empty or stale data
- No new evaluation logs for >5 minutes
- File size not growing: `ls -lh api/data/strategy_logs/swing-perp-16h.jsonl`

**Diagnosis:**
```powershell
# Check bot container status
docker ps | Select-String "bot_swing_btc"

# Check bot logs
docker logs heyanon_bot_swing_btc --tail 50

# Check for HTTP errors
docker logs heyanon_bot_swing_btc --tail 100 | Select-String "Failed|error|500|404"

# Verify API is receiving POST requests
docker logs heyanon_api --tail 50 | Select-String "POST /v1/strategies/swing-perp-16h/logs"
```

**Common Causes:**
1. **Bot container stopped/crashed**
   - **Check:** `docker ps -a | Select-String "bot_swing_btc"`
   - **Fix:** `docker-compose restart bot-swing-btc`
   - **Logs:** Check for Python exceptions in container logs

2. **Network connectivity issue:** Bot can't reach API
   - **Test:** `docker exec heyanon_bot_swing_btc curl http://api:8000/health`
   - **Fix:** Restart docker network: `docker-compose down && docker-compose up -d`

3. **API rejecting POSTs:** Authentication or validation errors
   - **Check API logs:** Look for `401 Unauthorized` or `422 Validation Error`
   - **Verify:** Bot has correct `HEYANON_API_KEY` env var
   - **Test manually:** `Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/strategies/swing-perp-16h/logs" -Headers @{"X-API-Key"="supersecret"} -Body '{"event":"test","market":"BTC","note":"test","score":50}' -ContentType "application/json"`

4. **Strategy code crashed:** best_1_6_16.py exception
   - **Check:** `docker logs heyanon_bot_swing_btc | Select-String "Traceback|Exception"`
   - **Common:** CoinBase API errors, pandas version mismatch
   - **Fix:** Check `bot/requirements.txt` dependencies

**Resolution Steps:**
1. Restart bot: `docker-compose restart bot-swing-btc`
2. Watch logs: `docker logs heyanon_bot_swing_btc -f`
3. Confirm evaluations resume: Should see "BTC STATUS" lines every 30s
4. Verify POST requests: `docker logs heyanon_api --tail 20 | Select-String "POST /v1/strategies/swing-perp-16h/logs"`

---

## 3. No Trades Visible

**Symptoms:**
- `/v1/strategies/swing-perp-16h/trades` returns `[]` empty array
- Position shows FLAT despite expecting open position
- Strategy evaluating but not executing

**Diagnosis:**
```powershell
# Check if trades file exists
docker exec heyanon_api ls -lh /app/data/strategy_trades/

# Check if bot is posting trades
docker logs heyanon_bot_swing_btc --tail 100 | Select-String "Trade posted|OPEN_LONG|CLOSE_LONG"

# Check recent logs for signal conditions
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=10" | ConvertTo-Json

# Verify position state
docker exec heyanon_api cat /app/data/strategy_state/swing-perp-16h.json | Select-String "position"
```

**Common Causes:**
1. **No trade signals generated yet:** Filters not aligned
   - **Check logs:** Look for "blocked" in recent evaluation notes
   - **Example:** `"0/4 long (blocked: no_fresh_WT_up,MFI1h<=50)"`
   - **OK:** This is normal — strategy waiting for 4/4 filter alignment
   - **Action:** Monitor logs, trades will appear when conditions met

2. **Bot not calling POST /trades:** Trade execution disabled
   - **Check:** `docker logs heyanon_bot_swing_btc | Select-String "_on_open|_on_close"`
   - **Verify:** Bot has trade callbacks registered
   - **Test:** Force a test trade (dev only): Set `SEND_TEST_TRADE=1` env var and restart bot

3. **Trades posting but file not persisting**
   - **Check API logs:** `docker logs heyanon_api | Select-String "POST /v1/strategies/swing-perp-16h/trades"`
   - **Verify directory:** `docker exec heyanon_api ls -la /app/data/strategy_trades/`
   - **Fix:** Ensure write permissions: `docker exec heyanon_api chmod -R 777 /app/data`

4. **Position computation broken:** Trades exist but position shows FLAT
   - **Check trades file:** `docker exec heyanon_api cat /app/data/strategy_trades/swing-perp-16h.jsonl`
   - **Verify sides:** Look for OPEN_LONG/CLOSE_LONG pairs
   - **Fix:** Restart API to recompute: `docker-compose restart api`

**Resolution Steps:**
1. **If filters blocked:** Wait for market conditions to align (this is expected behavior)
2. **If bot not posting:** Restart bot and verify callback registration
3. **If file missing:** Create manually: `docker exec heyanon_api touch /app/data/strategy_trades/swing-perp-16h.jsonl`
4. **If position wrong:** Restart API to trigger recomputation from trades file

---

## 4. Stale Data / Not Updating

**Symptoms:**
- `lastEvaluated` timestamp >5 minutes old
- Price not changing
- Logs show same data repeated

**Diagnosis:**
```powershell
# Check current timestamp vs lastEvaluated
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h" | Select-Object lastEvaluated

# Check bot evaluation frequency
docker logs heyanon_bot_swing_btc --tail 50 | Select-String "BTC STATUS"

# Verify API receiving POSTs
docker logs heyanon_api --tail 30 | Select-String "POST"
```

**Common Causes:**
1. **Bot stopped posting:** See section 2 above
2. **Evaluation interval too long:** Check `SNAPSHOT_INTERVAL_SEC` env var (should be 30)
3. **File writes blocked:** Disk full or permission issue
   - **Check:** `df -h` on host, `docker exec heyanon_api df -h`
   - **Check perms:** `docker exec heyanon_api ls -la /app/data`

**Resolution:**
- Restart bot: `docker-compose restart bot-swing-btc`
- Verify interval: `docker exec heyanon_bot_swing_btc env | Select-String "SNAPSHOT"`

---

## 5. Frontend Shows Wrong Data

**Symptoms:**
- Score显示 >100 or <0 (should be clamped 0-100)
- Labels showing as undefined
- Prices showing as 0.00

**Diagnosis:**
```powershell
# Test API response shape
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h" | ConvertTo-Json -Depth 10

# Check for null/missing fields
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=1" | ConvertTo-Json -Depth 5
```

**Common Causes:**
1. **Score not clamped:** Backend bug (should never happen, scores are clamped in POST handler)
   - **Fix:** Report bug, restart API as workaround
   
2. **Missing latestSignal:** No evaluations posted yet
   - **Check:** `latestSignal` field is `null` in API response
   - **OK:** Frontend should handle gracefully with "Waiting for first evaluation" message

3. **Frontend caching stale data**
   - **Clear:** Hard refresh (Ctrl+F5), clear browser cache
   - **Check:** Network tab shows recent timestamps in responses

**Resolution:**
- Verify API returns valid JSON schema per API_CONTRACT.md
- Frontend should use optional chaining: `strategy?.latestSignal?.score || 0`

---

## 6. Database Errors

**Note:** This strategy uses **file-based persistence only**. No database required for endpoints:
- `/v1/strategies/swing-perp-16h`
- `/v1/strategies/swing-perp-16h/logs`
- `/v1/strategies/swing-perp-16h/trades`
- `/v1/strategies/swing-perp-16h/roundtrips`

If you see Postgres errors in API logs, they are from **other legacy endpoints** and **do not affect** swing-perp-16h functionality.

**To verify file-based endpoints are working:**
```powershell
curl http://localhost:8000/v1/strategies/swing-perp-16h
curl http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=1
```

---

## Quick Commands Reference

```powershell
# Restart everything
docker-compose restart api bot-swing-btc

# View logs
docker logs heyanon_api --tail 50 -f
docker logs heyanon_bot_swing_btc --tail 50 -f

# Test endpoints
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/v1/strategies/swing-perp-16h
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=5"

# Check file sizes
docker exec heyanon_api ls -lh /app/data/strategy_logs/
docker exec heyanon_api ls -lh /app/data/strategy_trades/

# View file contents
docker exec heyanon_api tail -5 /app/data/strategy_logs/swing-perp-16h.jsonl
docker exec heyanon_api cat /app/data/strategy_state/swing-perp-16h.json

# Clear old logs (retain last 1000 lines)
docker exec heyanon_api sh -c "tail -1000 /app/data/strategy_logs/swing-perp-16h.jsonl > /tmp/temp.jsonl && mv /tmp/temp.jsonl /app/data/strategy_logs/swing-perp-16h.jsonl"
```

---

## Monitoring Checklist (Daily)

- [ ] Bot posting evaluations every 30s
- [ ] API responding <200ms (cached requests)
- [ ] Logs file growing (check size: `ls -lh api/data/strategy_logs/swing-perp-16h.jsonl`)
- [ ] lastEvaluated timestamp within last 2 minutes
- [ ] No HTTP 500 errors in API logs
- [ ] No Python exceptions in bot logs
- [ ] Frontend displays correct status badge (Active)

---

## Escalation

If issue persists after following runbook:
1. Check GitHub issues: https://github.com/Vince2kLyleStyle/Heyanon-platform/issues
2. Review API_CONTRACT.md for expected behavior
3. Collect logs: `docker logs heyanon_api > api.log && docker logs heyanon_bot_swing_btc > bot.log`
4. Post issue with logs attached

---

## Performance Targets (SLA)

- **API Response Time:** <200ms (cached), <2s (cold)
- **Evaluation Frequency:** Every 30s
- **Cache TTL:** 60s
- **Uptime:** 99.5% (excluding scheduled maintenance)

Current status: ✅ All targets met as of deployment
