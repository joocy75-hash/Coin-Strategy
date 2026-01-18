# Codebase Concerns

**Analysis Date:** 2026-01-19

## Tech Debt

**Hardcoded credentials in .env file:**
- Issue: `.env` file contains actual production API keys and tokens hardcoded
- Files: `/Users/mr.joo/Desktop/전략연구소/.env`
- Impact: Security risk - credentials exposed in version control history. TELEGRAM_BOT_TOKEN and BINANCE_API_KEY visible in plaintext
- Fix approach: Rotate all exposed credentials immediately. Use GitHub Secrets or HashiCorp Vault for production. Add `.env` validation to prevent commits with real keys

**Insufficient cash bug requiring explicit workarounds:**
- Issue: Backtesting framework with high-priced assets (BTC) fails due to insufficient initial capital calculation
- Files: `/Users/mr.joo/Desktop/전략연구소/quick_test_fixed_strategy.py` (lines 28-32, 373-382), `/Users/mr.joo/Desktop/전략연구소/optimize_adaptive_ml_moon_dev.py` (line 42), `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies/adaptive_ml_trailing_stop.py` (lines 355-382)
- Impact: Strategies generate zero trades, making metrics (Sharpe, Win Rate) NaN. Requires manual cash calculation workarounds in every test script
- Fix approach: Create centralized position sizing utility that calculates required capital based on asset price. Update Backtest initialization to auto-detect and set appropriate cash levels

**TODO placeholders in production code:**
- Issue: Multiple unimplemented features marked with TODO comments indicating incomplete functionality
- Files: `/Users/mr.joo/Desktop/전략연구소/multi_strategy_bot.py` (line 289 - Pine Script conversion), `/Users/mr.joo/Desktop/전략연구소/enhanced_strategies_batch/TEST_STRATEGY_001_enhanced.py` (lines 38-52), `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/src/orchestrator/scheduler.py` (line 479), `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/src/orchestrator/pipeline.py` (lines 555, 608), `/Users/mr.joo/Desktop/전략연구소/src/converter/pine_to_python.py` (line 486), `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/unified_converter.py` (line 338 - caching not implemented)
- Impact: Features advertised in documentation but not functional. Users may expect full Pine Script conversion or caching that doesn't work
- Fix approach: Either implement missing features or remove TODO stubs and update documentation to reflect actual capabilities

**Duplicate codebase (strategy-research-lab directory):**
- Issue: Entire codebase duplicated in `strategy-research-lab/` subdirectory creating maintenance nightmare
- Files: Duplicate copies of all `.py` files, configs, and documentation in `/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/`
- Impact: Changes must be made twice. High risk of divergence between copies. Unclear which is "source of truth"
- Fix approach: Remove duplicate directory. Use symlinks if needed for deployment. Consolidate to single source tree

**Return None/empty stubs masking errors:**
- Issue: Silent failures - functions return None/[]/{} instead of raising exceptions
- Files: `/Users/mr.joo/Desktop/전략연구소/api_manager.py` (lines 69, 113), `/Users/mr.joo/Desktop/전략연구소/src/storage/database.py` (lines 235, 241, 361, 551), `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 363, 369), `/Users/mr.joo/Desktop/전략연구소/src/collector/performance_parser.py` (lines 159, 170, 180, 192), `/Users/mr.joo/Desktop/전략연구소/src/backtester/production_generator.py` (lines 549, 563, 571, 815, 824)
- Impact: Errors propagate silently through system. Debugging difficult - no stack traces. Data corruption possible
- Fix approach: Replace silent returns with explicit exceptions. Add error logging. Use Result/Either pattern for expected failures

**Large monolithic files:**
- Issue: Files exceeding 1000 lines violate single responsibility principle
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (1094 lines), `/Users/mr.joo/Desktop/전략연구소/scripts/generate_beginner_report.py` (1012 lines), `/Users/mr.joo/Desktop/전략연구소/src/converter/indicator_mapper.py` (935 lines), `/Users/mr.joo/Desktop/전략연구소/src/converter/pine_parser.py` (926 lines), `/Users/mr.joo/Desktop/전략연구소/src/backtester/production_generator.py` (903 lines), `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/src/orchestrator/pipeline.py` (860 lines), `/Users/mr.joo/Desktop/전략연구소/src/storage/exporter.py` (823 lines), `/Users/mr.joo/Desktop/전략연구소/multi_strategy_bot.py` (816 lines)
- Impact: Difficult to test, review, and maintain. High cognitive load. Merge conflicts likely
- Fix approach: Extract logical modules. Split server.py into routers (strategies, backtest, live_trading). Break indicator_mapper into category-specific files

**Excessive sleep() calls:**
- Issue: 205 time.sleep/asyncio.sleep calls throughout codebase indicating timing-dependent logic
- Files: Pervasive across 68 files including `/Users/mr.joo/Desktop/전략연구소/src/collector/human_like_scraper.py`, `/Users/mr.joo/Desktop/전략연구소/src/collector/scripts_scraper.py`, `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/src/orchestrator/scheduler.py`
- Impact: Tests run slowly. Race conditions likely. Hard to predict execution time
- Fix approach: Replace fixed sleeps with event-driven waits. Use polling with exponential backoff. Mock sleeps in tests

## Known Bugs

**Entry condition too restrictive causing zero trades:**
- Symptoms: Backtests report 0 trades executed despite bullish market conditions. Sharpe Ratio and Win Rate show NaN
- Files: `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies/adaptive_ml_trailing_stop.py` (lines 355-367, documented as "BUGFIX")
- Trigger: Original logic only entered on exact -1 to 1 trend transition, which rarely occurs. Fixed by adding trend_confirmation and first_entry conditions
- Workaround: Patch applied in lines 355-382 with multiple entry conditions (reversal OR confirmation OR first_entry)

**Docker healthcheck timing issues:**
- Symptoms: Container marked unhealthy during startup, causing deployment failures
- Files: `/Users/mr.joo/Desktop/전략연구소/docker-compose.yml`, referenced in git history (commit 88fc4c7)
- Trigger: Application takes 60-90s to initialize database and start listening, but original healthcheck timeout was 60s
- Workaround: Increased start_period from 60s to 120s in healthcheck configuration

**Port confusion (8080 vs 8081):**
- Symptoms: Health checks fail with connection refused
- Files: `/Users/mr.joo/Desktop/전략연구소/DEPLOYMENT.md` (lines 54-58), referenced in git commit 28e2e3f
- Trigger: API server listens on 8080 inside container, mapped to 8081 on host, but scripts use wrong port
- Workaround: Documentation updated to specify port 8081 for all external access. Internal calls use 8080

**File permission errors in Docker volumes:**
- Symptoms: `PermissionError: /app/logs/api.log` crashes API server on startup
- Files: `/Users/mr.joo/Desktop/전략연구소/DEPLOYMENT.md` (lines 150-158), git commits 3b01ff5, 2dec796
- Trigger: Docker creates volumes with root ownership, but application runs as non-root user
- Workaround: `chmod -R 777 logs data` before container start. Better fix: use proper user mapping in Dockerfile

## Security Considerations

**Exposed API keys in .env file:**
- Risk: Telegram bot token, Binance API keys, and API secret visible in plaintext
- Files: `/Users/mr.joo/Desktop/전략연구소/.env` (lines 5, 9, 12-13)
- Current mitigation: `.env` file in `.gitignore`, but damage already done if previously committed
- Recommendations: Immediate key rotation. Use environment variables from orchestrator (GitHub Secrets, Docker secrets). Implement secret scanning pre-commit hook. Add .env to .gitignore exception list (never allow ANY .env commit)

**SQL Injection protection incomplete:**
- Risk: User input sanitization exists but not consistently applied
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 99-117 sanitize_input, validate_script_id), `/Users/mr.joo/Desktop/전략연구소/src/storage/database.py` (parameterized queries used)
- Current mitigation: Input validation with regex, parameterized queries in most places
- Recommendations: Audit all user input paths. Use ORM (SQLAlchemy) instead of raw SQL. Add integration tests for injection attempts. Consider using prepared statement library

**Rate limiting present but may be insufficient:**
- Risk: API endpoints rate-limited at 30-60 requests/minute per IP
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 169-183, 397, 408, 461, 543, 706, 750)
- Current mitigation: SlowAPI middleware with per-endpoint limits. Backtest endpoints limited to 5-10/min
- Recommendations: Add Redis-backed distributed rate limiting for multi-instance deployment. Implement API key-based quotas for authenticated users. Add circuit breakers for expensive operations (LLM calls, backtests)

**CORS misconfiguration risk:**
- Risk: CORS allows localhost origins which shouldn't be in production
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 286-299)
- Current mitigation: Hardcoded allow list includes production IP (141.164.55.245) but also localhost:3000, localhost:8080
- Recommendations: Remove localhost from production ALLOWED_ORIGINS. Use environment-based config. Set `allow_credentials=True` only if needed with strict origin whitelist

**No HTTPS/TLS encryption:**
- Risk: All traffic (including API keys in headers) transmitted in plaintext
- Files: `/Users/mr.joo/Desktop/전략연구소/DEPLOYMENT.md` (line 241 - SSL marked as optional)
- Current mitigation: None - HTTP only
- Recommendations: Add Nginx reverse proxy with Let's Encrypt SSL. Update all curl examples to use HTTPS. Enforce HTTPS redirect. Consider using Cloudflare for DDoS protection

## Performance Bottlenecks

**Synchronous database operations in async API:**
- Problem: API uses sqlite3 (synchronous) instead of aiosqlite despite being async FastAPI app
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (line 351 - `sqlite3.connect`), `/Users/mr.joo/Desktop/전략연구소/src/storage/database.py` (uses aiosqlite correctly)
- Cause: Mixing sync and async DB access patterns. API server uses sync sqlite3, storage layer uses async aiosqlite
- Improvement path: Convert API to use aiosqlite with async endpoints. Use connection pooling. Or use thread pool for sync operations with `run_in_executor`

**No caching layer for repeated queries:**
- Problem: Every API request hits database even for static data
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (stats, strategies endpoints), `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/unified_converter.py` (line 338 TODO: caching)
- Cause: No Redis or in-memory cache. Stats query aggregates analysis_json on every request
- Improvement path: Add Redis for frequently accessed data (stats, strategy list). Cache LLM responses with TTL. Use ETags for conditional requests

**LLM API calls without timeout:**
- Problem: Claude API calls can hang indefinitely
- Files: `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/llm_converter.py` (lines 201-209, 292-307)
- Cause: No timeout parameter in API client initialization. Retry logic exists but no timeout
- Improvement path: Add request timeout (30s). Implement circuit breaker pattern. Queue LLM requests with background workers to avoid blocking API

**Large file operations block event loop:**
- Problem: Reading/writing large strategy files synchronously in async context
- Files: `/Users/mr.joo/Desktop/전략연구소/src/storage/exporter.py` (823 lines), `/Users/mr.joo/Desktop/전략연구소/src/backtester/production_generator.py` (903 lines)
- Cause: File I/O done with standard open() instead of aiofiles in async functions
- Improvement path: Use aiofiles for all file operations. Stream large responses with generators. Move file processing to worker threads

**N+1 query problem in strategy listing:**
- Problem: Analysis JSON parsed individually for each strategy in results
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 503-528 - loops through rows parsing JSON)
- Cause: Filter logic requires parsing analysis_json client-side instead of in SQL
- Improvement path: Add computed columns (total_score, grade) to database. Create materialized view for common queries. Use JSON functions in SQLite for filtering

## Fragile Areas

**Web scraping with Playwright highly brittle:**
- Files: `/Users/mr.joo/Desktop/전략연구소/src/collector/human_like_scraper.py`, `/Users/mr.joo/Desktop/전략연구소/src/collector/scripts_scraper.py`, `/Users/mr.joo/Desktop/전략연구소/src/collector/pine_fetcher.py`
- Why fragile: TradingView can change selectors, add anti-bot measures, or change page structure at any time. Relies on exact DOM structure
- Safe modification: Always test against live TradingView site. Use data-testid attributes where available. Add retry logic with exponential backoff. Implement fallback selectors
- Test coverage: Limited - no mocked integration tests. Scripts in `/Users/mr.joo/Desktop/전략연구소/scripts/debug_tv.py` used for manual verification

**Pine Script to Python conversion via LLM:**
- Files: `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/llm_converter.py`, `/Users/mr.joo/Desktop/전략연구소/src/converter/pine_to_python.py`, `/Users/mr.joo/Desktop/전략연구소/src/converter/pine_parser.py`
- Why fragile: Depends on Claude API availability and prompt engineering. Pine Script syntax varies widely. Regex-based fallback in pine_to_python.py covers only basic cases
- Safe modification: Validate all LLM output with syntax checker. Run converted code in sandbox. Maintain extensive test suite of Pine->Python pairs. Version prompts in git
- Test coverage: Gaps - complex Pine features (security functions, arrays, custom types) not tested

**Docker deployment SSH timeout issues:**
- Files: `/Users/mr.joo/Desktop/전략연구소/.github/workflows/deploy.yml` (likely), `/Users/mr.joo/Desktop/전략연구소/DEPLOYMENT.md` (lines 132-140)
- Why fragile: GitHub Actions SSH to server can timeout during image build. Network flaky. Build can take 5-10 minutes
- Safe modification: Use manual deployment for major changes. Test docker-compose.yml changes locally first. Keep images small to reduce build time
- Test coverage: None - no automated deployment tests. Reliance on production testing

**Strategy backtesting data pipeline:**
- Files: `/Users/mr.joo/Desktop/전략연구소/src/backtester/backtest_engine.py`, `/Users/mr.joo/Desktop/전략연구소/src/backtester/strategy_tester.py`, `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/src/backtest/engine.py`
- Why fragile: Depends on CCXT for market data (APIs change), vectorbt for calculations (complex library), and backtesting.py framework (strict input requirements). Position sizing bugs still present
- Safe modification: Freeze CCXT version. Validate all input data (no NaN, monotonic timestamps). Add data quality checks. Test with known-good datasets
- Test coverage: Basic tests exist in `/Users/mr.joo/Desktop/전략연구소/tests/test_backtest_engine.py` but don't cover edge cases

## Scaling Limits

**SQLite single-writer limitation:**
- Current capacity: ~1000 concurrent read requests, but only 1 write at a time
- Limit: Heavy write traffic (strategy collection, analysis updates) will create lock contention. Write queue buildup
- Scaling path: Migrate to PostgreSQL for production. Use write-ahead logging (WAL) mode for SQLite. Implement write batching. Separate read replicas

**Single-server deployment:**
- Current capacity: 4GB RAM, 75GB disk on single Hetzner VPS (141.164.55.245)
- Limit: No horizontal scaling. Single point of failure. Disk fills at ~45% currently, will fill with more strategy data
- Scaling path: Containerize with Kubernetes. Add load balancer. Use managed database (Supabase, PlanetScale). Implement CDN for static assets

**Synchronous LLM calls blocking API:**
- Current capacity: 10 requests/minute rate limit on backtest endpoint
- Limit: Each LLM conversion takes 10-30s. Under load, request queue grows unbounded
- Scaling path: Move LLM calls to background job queue (Celery, Bull). Return 202 Accepted with job ID. Implement webhook callbacks. Use streaming responses

**No connection pooling:**
- Current capacity: Each request opens new DB connection
- Limit: File descriptor exhaustion at ~1000 concurrent connections. Connection overhead adds 10-50ms latency
- Scaling path: Use connection pool (aiosqlite-pool, SQLAlchemy pool). Set max_connections limit. Add connection health checks

## Dependencies at Risk

**Playwright automation detection:**
- Risk: TradingView or other sites may detect and block Playwright automation
- Impact: Strategy collection pipeline completely broken. 71 strategies currently collected may be max
- Migration plan: Implement API-based collection if TradingView offers API. Use rotating proxies. Add stealth mode enhancements. Consider manual collection for critical strategies

**OpenAI SDK for Claude API:**
- Risk: Using `openai>=1.6.0` package for Anthropic Claude via compatibility layer
- Impact: Breaking changes in OpenAI SDK may affect Claude calls. Anthropic SDK (`anthropic>=0.40.0`) preferred
- Migration plan: Already have both SDKs in requirements.txt. Switch llm_converter.py to use anthropic SDK directly. Update prompts to use Claude-specific features (thinking blocks, extended context)

**PyNEScript parser unmaintained:**
- Risk: `pynescript>=0.2.0` last updated 2+ years ago. May not support Pine Script v5/v6 features
- Impact: AST parsing fails for modern strategies. Fallback to regex-based conversion loses accuracy
- Migration plan: Fork pynescript and maintain internally. Or build custom parser using ANTLR grammar. Document unsupported Pine features

**VectorBT version pinning needed:**
- Risk: `vectorbt>=0.26.0` uses >= instead of ~=, allowing breaking changes
- Impact: Update to vectorbt 1.0+ could break backtest calculations
- Migration plan: Pin to `vectorbt~=0.26.0`. Test upgrades in staging. Consider switching to backtesting.py only (already used) to reduce dependencies

**Torch dependency bloat:**
- Risk: `torch` package adds 2.5GB+ to Docker image for FinBERT (sentiment analysis)
- Impact: Slow deployments, high disk usage, not actively used in production
- Migration plan: Make torch optional dependency. Use CPU-only build. Or remove FinBERT entirely if sentiment analysis not used

## Missing Critical Features

**No authentication on API endpoints:**
- Problem: `/api/backtest` and `/api/emergency-stop` should require auth but API key validation is optional
- Blocks: Secure production deployment. Anyone can trigger expensive backtest operations or stop trading
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 849-856 - `verify_api_key` returns True if no key set, lines 904, 944 - emergency stop requires key but development mode bypasses)
- Priority: High

**No trade execution logging:**
- Problem: Live trading mentioned but no persistent trade history database
- Blocks: Tax reporting, performance analysis, compliance auditing
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py` (lines 978-1084 - trade endpoints defined but logger import may fail), `/Users/mr.joo/Desktop/전략연구소/src/logging/trade_logger.py` (referenced but may not exist in all directories)
- Priority: High - required before live trading

**No backtest result caching:**
- Problem: Same strategy on same data re-runs full backtest every time
- Blocks: Fast iteration, API responsiveness
- Files: `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/unified_converter.py` (line 338 - TODO comment)
- Priority: Medium

**No monitoring/alerting:**
- Problem: No Prometheus metrics, health check dashboard, or error alerting
- Blocks: Production operations, incident response
- Files: `/Users/mr.joo/Desktop/전략연구소/DEPLOYMENT.md` (monitoring section absent)
- Priority: Medium

**No database migration system:**
- Problem: Schema changes done manually with SQL. No version tracking
- Blocks: Safe deployments, rollbacks, multi-environment consistency
- Files: `/Users/mr.joo/Desktop/전략연구소/src/storage/database.py` (lines 61-106 - CREATE TABLE IF NOT EXISTS, no versioning)
- Priority: Medium

## Test Coverage Gaps

**Web scraping integration:**
- What's not tested: Live TradingView site scraping, pagination, rate limiting, anti-bot detection
- Files: `/Users/mr.joo/Desktop/전략연구소/src/collector/scripts_scraper.py`, `/Users/mr.joo/Desktop/전략연구소/src/collector/pine_fetcher.py`
- Risk: Scraping breaks silently in production. Collection pipeline unmonitored
- Priority: High

**LLM conversion quality:**
- What's not tested: Claude API responses, conversion accuracy for complex Pine indicators, Python syntax validation
- Files: `/Users/mr.joo/Desktop/전략연구소/src/converter/llm/llm_converter.py`, `/Users/mr.joo/Desktop/전략연구소/src/converter/pine_parser.py`
- Risk: Generated code may not run. Silent failures in conversion produce invalid strategies
- Priority: High

**Position sizing edge cases:**
- What's not tested: Zero balance, insufficient margin, partial fills, high-priced assets (>$50k)
- Files: `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies/adaptive_ml_trailing_stop.py` (lines 373-382)
- Risk: Same bug recurs in new strategies. Production trades rejected by exchange
- Priority: High

**Docker deployment:**
- What's not tested: Container health, volume permissions, multi-container networking, secret injection
- Files: `/Users/mr.joo/Desktop/전략연구소/Dockerfile`, `/Users/mr.joo/Desktop/전략연구소/docker-compose.yml`
- Risk: Deployment failures discovered in production. No rollback testing
- Priority: Medium

**API error handling:**
- What's not tested: Malformed requests, SQL injection attempts, rate limit exhaustion, database locked scenarios
- Files: `/Users/mr.joo/Desktop/전략연구소/api/server.py`, `/Users/mr.joo/Desktop/전략연구소/tests/test_api.py`
- Risk: 500 errors in production. Security vulnerabilities undiscovered
- Priority: Medium

---

*Concerns audit: 2026-01-19*
