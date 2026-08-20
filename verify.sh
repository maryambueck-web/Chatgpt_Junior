#!/usr/bin/env bash
# Local production-readiness check: builds the real Docker image, runs it
# through docker-compose exactly as a host with a persistent disk would, and
# exercises it — not just "does it start", but "does data survive a restart"
# and "do the actual API integrations work end to end".
#
# Usage:
#   ./verify.sh              # build, run, verify, leave it running
#   ./verify.sh --down       # same, then tear down the container at the end
#   ./verify.sh --no-build   # skip `docker compose build` (reuse existing image)
#
# Exit code is non-zero if anything failed, so this is CI-usable.

set -uo pipefail

TEAR_DOWN=false
BUILD_FLAG="--build"
for arg in "$@"; do
  case "$arg" in
    --down) TEAR_DOWN=true ;;
    --no-build) BUILD_FLAG="" ;;
  esac
done

# Newer Docker Desktop bundles Compose as `docker compose` (a plugin
# subcommand); older/standalone installs only have the hyphenated
# `docker-compose` binary. Detect whichever actually exists rather than
# hardcoding one and failing immediately on the other.
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "Neither 'docker compose' nor 'docker-compose' is available. Install Docker Desktop (bundles both) or the standalone docker-compose." >&2
  exit 1
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() { echo -e "${GREEN}PASS${NC}  $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo -e "${RED}FAIL${NC}  $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo -e "${YELLOW}WARN${NC}  $1"; WARN_COUNT=$((WARN_COUNT + 1)); }

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "== 1. Unit / regression tests =="
if [ -x ".venv/bin/python" ]; then
  if .venv/bin/python -m pytest -q; then pass "pytest suite"; else fail "pytest suite — fix these before trusting anything below"; fi
else
  warn "no .venv found — skipping local pytest run (the suite still runs fine, just couldn't find your venv)"
fi

echo
echo "== 2. Config sanity (.env) =="
if [ ! -f .env ]; then
  warn ".env not found — the container will run in mock-ChatGPT / picsum-fallback / default-PIN mode"
else
  grep -q '^PARENT_PIN=' .env && ! grep -q '^PARENT_PIN=1234' .env \
    && pass "PARENT_PIN is set to a non-default value" \
    || warn "PARENT_PIN is unset or still 1234 — fine for this local test, change it before real deployment"
  # chatgpt_adapter.py accepts either naming — DEEPSEEK_* is equally valid.
  grep -qE '^(OPENAI|DEEPSEEK)_API_KEY=' .env && ! grep -q '^OPENAI_API_KEY=your_key_here' .env \
    && pass "an API key is set (OPENAI_API_KEY or DEEPSEEK_API_KEY)" \
    || warn "no OPENAI_API_KEY or DEEPSEEK_API_KEY set — the app will run in mock ChatGPT mode"
  grep -q '^UNSPLASH_ACCESS_KEY=' .env && ! grep -q '^UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here' .env \
    && pass "UNSPLASH_ACCESS_KEY is set" \
    || warn "UNSPLASH_ACCESS_KEY is unset — image requests will use the picsum.photos fallback, not real search"
fi

echo
echo "== 3. Build and start the real container =="
if ! $DC up -d $BUILD_FLAG; then
  fail "$DC up failed — stopping here, everything below depends on this"
  echo; echo "Result: $PASS_COUNT passed, $FAIL_COUNT failed, $WARN_COUNT warnings"
  exit 1
fi
pass "container started"

CID=$($DC ps -q safechatgpt)

echo
echo "== 4. Wait for health check =="
READY=false
for _ in $(seq 1 30); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CID" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then READY=true; break; fi
  sleep 2
done
if $READY; then
  pass "container reports healthy"
else
  fail "container never became healthy (last status: $STATUS) — check: $DC logs"
  $DC logs --tail=40
fi

echo
echo "== 5. HTTP smoke checks =="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/ || echo "000")
[ "$HTTP_CODE" = "200" ] && pass "home page responds (HTTP $HTTP_CODE)" || fail "home page did not respond (HTTP $HTTP_CODE)"

HEALTH_BODY=$(curl -s http://localhost:8501/_stcore/health || echo "")
[ "$HEALTH_BODY" = "ok" ] && pass "health endpoint returns 'ok'" || fail "health endpoint returned unexpected body: '$HEALTH_BODY'"

echo
echo "== 6. In-container integration checks =="
# Runs the actual app modules inside the container, the same way app.py does,
# so this catches real integration issues (bad key, network egress blocked,
# import errors) rather than just "the process is listening on a port".
INTEGRATION_OUTPUT=$($DC exec -T safechatgpt python -c "
import sys
sys.path.insert(0, 'src')
import shared_store as ss
import chatgpt_adapter
import image_service

# Settings/log round trip against the actual mounted volume path.
ss.save_settings({**ss.load_settings(), 'age_band': '11-13'})
before = len(ss.load_log())
ss.append_log_entry({'stage': 'Verify', 'action': 'ALLOW', 'category': 'general', 'severity': 'low', 'explanation': 'verify.sh smoke test'})
after = len(ss.load_log())
print('STORAGE_OK' if after == before + 1 else 'STORAGE_FAIL')

reply = chatgpt_adapter.call_chatgpt([{'role': 'user', 'content': 'Say OK'}])
print('CHATGPT_MOCK_OK' if 'mock mode' in reply.lower() else 'CHATGPT_REAL_REPLY:' + reply[:60].replace(chr(10), ' '))

url = image_service.fetch_image('show me a picture of a sunflower', '11-13', session_id='verify')
print('IMAGE_URL:' + str(url))
" 2>&1)

echo "$INTEGRATION_OUTPUT" | sed 's/^/       /'

echo "$INTEGRATION_OUTPUT" | grep -q "STORAGE_OK" && pass "settings/log round-trip against the mounted volume" || fail "settings/log round-trip failed — see output above"
echo "$INTEGRATION_OUTPUT" | grep -qE "CHATGPT_MOCK_OK|CHATGPT_REAL_REPLY" && pass "ChatGPT adapter responded (mock or real — see output above)" || fail "ChatGPT adapter call failed — see output above"
echo "$INTEGRATION_OUTPUT" | grep -q "IMAGE_URL:http" && pass "image_service returned a URL (see output above for which source)" || fail "image_service did not return a URL — see output above"

echo
echo "== 7. Persistence across a restart =="
BEFORE_COUNT=$($DC exec -T safechatgpt python -c "
import sys; sys.path.insert(0, 'src')
import shared_store as ss
print(len(ss.load_log()))
" 2>/dev/null | tr -d '\r')

$DC restart safechatgpt >/dev/null 2>&1

READY=false
for _ in $(seq 1 30); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CID" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then READY=true; break; fi
  sleep 2
done

AFTER_COUNT=$($DC exec -T safechatgpt python -c "
import sys; sys.path.insert(0, 'src')
import shared_store as ss
print(len(ss.load_log()))
" 2>/dev/null | tr -d '\r')

if $READY && [ "$AFTER_COUNT" = "$BEFORE_COUNT" ] && [ -n "$BEFORE_COUNT" ]; then
  pass "log entries survived a container restart ($BEFORE_COUNT entries before and after)"
else
  fail "data did NOT survive the restart (before: $BEFORE_COUNT, after: $AFTER_COUNT) — check the volume mount"
fi

echo
echo "======================================"
echo "Result: $PASS_COUNT passed, $FAIL_COUNT failed, $WARN_COUNT warnings"
echo "======================================"

if $TEAR_DOWN; then
  echo "Tearing down (--down was passed)..."
  $DC down
else
  echo "Container left running at http://localhost:8501 — '$DC down' when you're done, or re-run with --down."
fi

[ "$FAIL_COUNT" -eq 0 ]
