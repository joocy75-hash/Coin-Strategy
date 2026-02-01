# External Integrations

**Analysis Date:** 2026-01-19

## APIs & External Services

**AI/LLM Services:**
- Anthropic Claude - Primary LLM for deep strategy analysis
  - SDK/Client: anthropic>=0.40.0
  - Auth: ANTHROPIC_API_KEY (env var)
  - Model: claude-3-5-sonnet-20241022 (configurable via LLM_MODEL)
  - Usage: `src/analyzer/llm/deep_analyzer.py`, `src/converter/llm/`

- OpenAI GPT - Alternative LLM for analysis
  - SDK/Client: openai>=1.6.0
  - Auth: OPENAI_API_KEY (env var)
  - Model: gpt-4o (default, configurable)
  - Usage: Hybrid conversion, fallback analysis

**Cryptocurrency Data:**
- Binance Exchange API - Market data and backtesting
  - SDK/Client: ccxt>=4.2.0
  - Auth: BINANCE_API_KEY, BINANCE_API_SECRET (env vars)
  - Connection: Async support via ccxt.async_support
  - Usage: `src/backtester/data_collector.py`, `multi_strategy_bot.py`
  - Testnet: Configurable via USE_TESTNET env var

**Web Scraping:**
- TradingView Scripts - Strategy collection source
  - URL: https://www.tradingview.com/scripts/
  - Client: Playwright browser automation
  - Anti-bot: playwright-stealth, human-like scraping patterns
  - Usage: `src/collector/human_like_scraper.py`, `src/collector/scripts_scraper.py`

## Data Storage

**Databases:**
- SQLite
  - Connection: DB_PATH env var (default: data/strategies.db)
  - Client: aiosqlite (async ORM)
  - Schema: `src/storage/database.py` (StrategyDatabase class)
  - Tables: strategies (script_id, title, author, pine_code, performance_json, analysis_json)

**File Storage:**
- Local filesystem only
  - Converted strategies: OUTPUT_DIR (default: data/converted)
  - Reports: data/reports
  - Logs: LOGS_DIR (default: logs)
  - Cached data: Parquet files via pyarrow

**Caching:**
- Parquet-based cache for LLM conversion results
  - Location: `src/converter/llm/conversion_cache.py`
  - Backend: pyarrow>=14.0.0

## Authentication & Identity

**Auth Provider:**
- Custom secure storage
  - Implementation: `encrypted_api_manager.py` (SecureAPIManager)
  - Encryption: Fernet symmetric encryption (cryptography library)
  - Master key: MASTER_ENCRYPTION_KEY env var
  - Storage: .secure_keys/ directory (encrypted JSON files)

## Monitoring & Observability

**Error Tracking:**
- None (file-based logging only)

**Logs:**
- Structured JSON logging
  - File: logs/api.json.log (10MB rotation, 5 backups)
  - Text: logs/api.log (human-readable)
  - Handler: RotatingFileHandler from logging.handlers
  - Format: ISO timestamps, request IDs, execution times

**Live Trading Safeguards:**
- Custom implementation
  - Module: `src/trading/live_safeguards.py`
  - Features: Emergency stop, drawdown limits, consecutive loss tracking
  - State file: .trading_state.json

## CI/CD & Deployment

**Hosting:**
- Hetzner VPS (141.164.55.245)
  - Path: /root/service_c/strategy-research-lab
  - Group: Service Group C (isolated resources)

**CI Pipeline:**
- GitHub Actions
  - Workflow: `.github/workflows/deploy.yml`
  - Trigger: Push to main branch or manual dispatch
  - Steps: SSH deploy, rsync, Docker build, health check
  - Secrets: SSH_PRIVATE_KEY, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

**Container Registry:**
- None (builds on-server from source)

## Environment Configuration

**Required env vars:**
- ANTHROPIC_API_KEY or OPENAI_API_KEY - LLM access
- DB_PATH - Database location
- HEADLESS - Browser mode for scraping (true in production)
- LLM_MODEL - Model selection
- LOGS_DIR - Log file directory

**Optional env vars:**
- BINANCE_API_KEY, BINANCE_API_SECRET - Live trading (paper trading if not set)
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID - Notifications
- API_SECRET_KEY - API authentication for emergency stop
- MASTER_ENCRYPTION_KEY, ENCRYPTION_SALT - Secure key storage
- USE_TESTNET, PAPER_TRADING - Trading mode flags
- MAX_STRATEGIES, MIN_LIKES, RATE_LIMIT_DELAY - Scraping limits

**Secrets location:**
- GitHub repository secrets (CI/CD)
- Server .env file (production)
- .secure_keys/ directory (encrypted API keys)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- Telegram notifications
  - Endpoint: https://api.telegram.org/bot{token}/sendMessage
  - Usage: `src/notification/telegram_bot.py`, `notification_system.py`
  - Events: Deployment status, trading signals, emergency stops

**Health Check:**
- HTTP GET /api/health
  - Implementation: `api/server.py` line 396
  - Returns: {status, timestamp, database_exists}
  - Docker healthcheck: 30s interval, 120s start period

## Rate Limiting

**API Server:**
- slowapi middleware
  - Default: 60/minute (health), 30/minute (strategies), 10/minute (backtest)
  - Key function: get_remote_address
  - Handler: _rate_limit_exceeded_handler

**TradingView Scraping:**
- Custom rate limiting
  - Delay: RATE_LIMIT_DELAY env var (default: 1.0 seconds)
  - Human-like delays: 10-30 seconds random intervals
  - Session persistence: data/.tv_session.json

**LLM API Calls:**
- Exponential backoff via tenacity
  - Max retries: MAX_RETRIES env var (default: 3)
  - Cost optimization: `src/analyzer/llm/cost_optimizer.py`

---

*Integration audit: 2026-01-19*
