# Architecture

**Analysis Date:** 2026-01-19

## Pattern Overview

**Overall:** Pipeline-based Architecture with Async/Await Pattern

**Key Characteristics:**
- Multi-stage data pipeline: Collect → Analyze → Convert → Backtest → Trade
- Async-first design using asyncio for I/O-bound operations
- Service-oriented modules with clear separation of concerns
- REST API layer for external access
- Database-backed persistence with SQLite

## Layers

**API Layer:**
- Purpose: HTTP interface for external clients and dashboards
- Location: `api/`
- Contains: FastAPI server, endpoints, middleware
- Depends on: Storage, Backtester, Trading modules
- Used by: Web dashboards, external tools, monitoring systems

**Orchestration Layer:**
- Purpose: Coordinates multi-stage pipeline execution
- Location: `main.py`
- Contains: Pipeline orchestration, CLI argument parsing, logging setup
- Depends on: All src modules (collector, analyzer, converter, storage)
- Used by: Manual runs, scheduled jobs (Docker)

**Collection Layer:**
- Purpose: Web scraping TradingView for strategy metadata and Pine Script code
- Location: `src/collector/`
- Contains: Playwright scrapers, session management, performance parsing
- Depends on: Storage (database writes)
- Used by: Orchestration layer, scheduled collector service

**Analysis Layer:**
- Purpose: Quality scoring, repainting detection, overfitting analysis
- Location: `src/analyzer/`
- Contains: Rule-based detectors, LLM analyzers (Claude), scoring logic
- Depends on: Storage (read/write analysis results)
- Used by: Orchestration layer

**Conversion Layer:**
- Purpose: Transform Pine Script to executable Python strategies
- Location: `src/converter/`
- Contains: Lexer, parser, AST builder, rule-based converter, LLM fallback
- Depends on: Analyzer (for validation), Storage
- Used by: Orchestration layer, API (on-demand conversion)

**Backtesting Layer:**
- Purpose: Historical performance testing of converted strategies
- Location: `src/backtester/`
- Contains: VectorBT engine, data collection, performance metrics
- Depends on: Converter (Python strategies), Storage
- Used by: API endpoints, orchestration layer

**Trading Layer:**
- Purpose: Live trading safeguards and risk management
- Location: `src/trading/`
- Contains: Safeguards, position sizing, emergency stop mechanisms
- Depends on: Storage (trade logging)
- Used by: Live trading bots (external scripts)

**Storage Layer:**
- Purpose: Persistent data management
- Location: `src/storage/`
- Contains: Async SQLite wrapper, models, exporter utilities
- Depends on: None (foundation layer)
- Used by: All layers above

**Notification Layer:**
- Purpose: External alerting and reporting
- Location: `src/notification/`
- Contains: Telegram bot integration
- Depends on: Storage (reading trade data)
- Used by: Trading layer, backtester

**Logging Layer:**
- Purpose: Structured logging and audit trails
- Location: `src/logging/`
- Contains: Trade logger, JSON log formatters
- Depends on: None
- Used by: API, Trading, Backtester

## Data Flow

**Collection Pipeline:**

1. Scheduled trigger (cron or manual) → `main.py` or `scripts/auto_collector_service.py`
2. `TVScriptsScraper` fetches strategy list from TradingView
3. `PineCodeFetcher` extracts Pine Script source code per strategy
4. `StrategyDatabase.save_strategy()` persists to `data/strategies.db`

**Analysis Pipeline:**

1. Load strategies from database (those without analysis)
2. `StrategyScorer` orchestrates analysis:
   - `RepaintingDetector` (rule-based) checks for future data leaks
   - `OverfittingDetector` (rule-based) identifies overfitting patterns
   - `LLMDeepAnalyzer` (Claude API) performs semantic analysis
3. Score aggregation (A-F grading)
4. Results saved to `analysis_json` field in database

**Conversion Pipeline:**

1. Load high-scoring strategies (B grade or above)
2. `RuleBasedConverter` attempts AST-based conversion
3. If complexity exceeds threshold → `HybridConverter` uses LLM
4. Generated Python code written to `data/converted/`
5. Path stored in database

**Backtest Pipeline:**

1. API request `/api/backtest` or batch script
2. `StrategyTester` loads converted Python strategy
3. `DataCollector` fetches historical OHLCV data
4. `VectorBTEngine` executes vectorized backtest
5. Metrics (Sharpe, drawdown, returns) stored in `analysis_json`

**Live Trading Flow:**

1. External bot loads production strategy
2. `LiveSafeguards` validates each trade signal
3. Emergency stop check → API `/api/emergency-stop`
4. Trade executed via ccxt (Binance)
5. `TradeLogger` records transaction to `logs/trades/`

**State Management:**
- Database as single source of truth (SQLite)
- In-memory caching for active sessions (Playwright)
- File-based state for emergency stops (`.trading_state.json`)

## Key Abstractions

**StrategyMeta:**
- Purpose: Immutable metadata for a TradingView strategy
- Examples: `src/collector/scripts_scraper.py`
- Pattern: Dataclass with script_id, title, author, likes, URL

**PineAST:**
- Purpose: Abstract syntax tree representation of Pine Script
- Examples: `src/converter/pine_parser.py`
- Pattern: Composite pattern with node types (Input, Variable, Function, Plot, Condition)

**FinalScore:**
- Purpose: Aggregated quality score with grading
- Examples: `src/analyzer/scorer.py`
- Pattern: Dataclass with total_score, grade, repainting_score, overfitting_score

**StrategyModel:**
- Purpose: Complete strategy record for database
- Examples: `src/storage/models.py`
- Pattern: Dataclass mapping to SQLite table schema

**TransformationContext:**
- Purpose: Stateful context for Pine → Python conversion
- Examples: `src/converter/transformation_context.py`
- Pattern: Builder pattern accumulating variables, imports, conditions

## Entry Points

**Main Pipeline:**
- Location: `main.py`
- Triggers: CLI execution (`python main.py --max-strategies 100`)
- Responsibilities: Orchestrate collect → analyze → convert workflow

**API Server:**
- Location: `api/server.py`
- Triggers: HTTP requests, Docker container startup
- Responsibilities: Serve REST API, health checks, backtest endpoints

**Auto Collector Service:**
- Location: `scripts/auto_collector_service.py`
- Triggers: Cron/timer (6-hour intervals in production)
- Responsibilities: Automated strategy collection without manual intervention

**Test Suite:**
- Location: `tests/test_*.py`
- Triggers: pytest command
- Responsibilities: Validate all modules with 172 test cases

## Error Handling

**Strategy:** Fail-fast for critical errors, graceful degradation for analysis failures

**Patterns:**
- Async exceptions wrapped in try/except with logging
- Database errors raise HTTPException (API) or re-raised (pipeline)
- LLM API failures (rate limits, timeouts) → retry logic with exponential backoff
- Conversion errors → fallback to simpler strategy or mark as "manual review needed"
- Missing dependencies logged but don't halt pipeline (optional features)

## Cross-Cutting Concerns

**Logging:**
- Python `logging` module with structured JSON output
- API uses RotatingFileHandler (10MB rotation)
- Request IDs for tracing API calls

**Validation:**
- Pydantic models for API request/response validation
- Input sanitization (SQL injection, XSS prevention) in API layer
- Script ID validation (alphanumeric, hyphens, underscores only)

**Authentication:**
- API key-based auth for sensitive endpoints (`/emergency-stop`, `/trades/export`)
- Environment variable `API_SECRET_KEY`
- Rate limiting via slowapi (30-60 requests/minute)

---

*Architecture analysis: 2026-01-19*
