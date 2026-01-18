# Codebase Structure

**Analysis Date:** 2026-01-19

## Directory Layout

```
전략연구소/
├── api/                        # FastAPI REST server
├── src/                        # Core application modules
│   ├── analyzer/               # Strategy quality analysis
│   ├── backtester/             # Historical performance testing
│   ├── collector/              # TradingView scraping
│   ├── converter/              # Pine → Python conversion
│   ├── logging/                # Trade logging
│   ├── notification/           # Telegram alerts
│   ├── platform_integration/   # External platform connectors
│   ├── storage/                # Database layer
│   └── trading/                # Live trading safeguards
├── scripts/                    # Utility scripts and services
├── tests/                      # Test suite (172 tests)
├── deploy/                     # Deployment configs
├── templates/                  # HTML dashboards
├── data/                       # Runtime data (DB, reports, market data)
├── logs/                       # Application logs
├── examples/                   # Usage examples
├── .github/workflows/          # CI/CD pipelines
├── main.py                     # Main orchestration entry point
├── docker-compose.yml          # Production deployment
├── requirements.txt            # Python dependencies
└── .env                        # Environment configuration
```

## Directory Purposes

**api/**
- Purpose: HTTP API layer for external access
- Contains: `server.py` (FastAPI app), `__init__.py`
- Key files: `api/server.py` (1095 lines, all endpoints)

**src/analyzer/**
- Purpose: AI-powered strategy quality analysis
- Contains: Rule-based detectors, LLM analyzers, scoring logic
- Key files:
  - `src/analyzer/scorer.py`: Main scoring orchestration
  - `src/analyzer/pine_parser.py`: Pine Script AST parser
  - `src/analyzer/rule_based/repainting_detector.py`: Repainting detection
  - `src/analyzer/rule_based/overfitting_detector.py`: Overfitting analysis
  - `src/analyzer/llm/deep_analyzer.py`: Claude-based semantic analysis
  - `src/analyzer/sentiment_analyzer.py`: FinBERT sentiment analysis

**src/backtester/**
- Purpose: Historical strategy testing infrastructure
- Contains: VectorBT engine, data collectors, performance generators
- Key files:
  - `src/backtester/vectorbt_engine.py`: High-performance backtesting
  - `src/backtester/strategy_tester.py`: Strategy execution wrapper
  - `src/backtester/production_generator.py`: Production-ready code generation
  - `src/backtester/data_collector.py`: Market data fetching

**src/collector/**
- Purpose: TradingView web scraping and data extraction
- Contains: Playwright scrapers, session managers, code fetchers
- Key files:
  - `src/collector/scripts_scraper.py`: Strategy metadata scraping
  - `src/collector/pine_fetcher.py`: Pine Script code extraction
  - `src/collector/session_manager.py`: Browser session handling
  - `src/collector/performance_parser.py`: TradingView metrics parsing

**src/converter/**
- Purpose: Pine Script to Python transformation
- Contains: Lexer, parser, AST, rule-based converter, LLM fallback
- Key files:
  - `src/converter/pine_parser.py`: Pine AST builder
  - `src/converter/rule_based_converter.py`: Main conversion logic
  - `src/converter/llm/hybrid_converter.py`: LLM-assisted conversion
  - `src/converter/strategy_generator.py`: Final Python code generation
  - `src/converter/expression_transformer.py`: Expression translation
  - `src/converter/template_manager.py`: Code templates

**src/logging/**
- Purpose: Structured logging and trade audit trails
- Contains: Trade loggers, JSON formatters
- Key files:
  - `src/logging/trade_logger.py`: Trade transaction logging

**src/notification/**
- Purpose: External alerting systems
- Contains: Telegram bot integration
- Key files:
  - `src/notification/telegram_bot.py`: Telegram notification sender

**src/platform_integration/**
- Purpose: Integration with external trading platforms
- Contains: Strategy registrars, deployment utilities
- Key files:
  - `src/platform_integration/deployer.py`: Platform deployment
  - `src/platform_integration/strategy_registrar.py`: Strategy registration

**src/storage/**
- Purpose: Database abstraction and persistence
- Contains: Async SQLite wrapper, models, exporters
- Key files:
  - `src/storage/database.py`: Main database interface
  - `src/storage/models.py`: Data models (StrategyModel, AnalysisResultModel)
  - `src/storage/exporter.py`: Export utilities (CSV, JSON)

**src/trading/**
- Purpose: Live trading safety mechanisms
- Contains: Safeguards, risk checks, emergency stops
- Key files:
  - `src/trading/live_safeguards.py`: Position sizing, loss limits, slippage checks

**scripts/**
- Purpose: Automation scripts and maintenance tools
- Contains: Collectors, analyzers, report generators
- Key files:
  - `scripts/auto_collector_service.py`: Scheduled collection service
  - `scripts/generate_report.py`: HTML report generation
  - `scripts/generate_beginner_report.py`: Beginner-friendly dashboard
  - `scripts/run_collector.py`: Manual collection trigger
  - `scripts/run_analyzer.py`: Manual analysis trigger
  - `scripts/run_converter.py`: Manual conversion trigger

**tests/**
- Purpose: Automated testing suite
- Contains: Unit tests, integration tests, API tests
- Key files:
  - `tests/test_api.py`: API endpoint tests
  - `tests/test_collector.py`: Scraper tests
  - `tests/test_scorer.py`: Analysis tests
  - `tests/test_integration.py`: End-to-end tests
  - `tests/conftest.py`: Pytest fixtures

**deploy/**
- Purpose: Production deployment configurations
- Contains: systemd services, shell scripts, proxy configs
- Key files:
  - `deploy/setup_server.sh`: Server initialization
  - `deploy/deploy.sh`: Deployment automation
  - `deploy/strategy-collector.service`: Systemd service for auto-collection
  - `deploy/proxy/conf.d/`: Nginx reverse proxy configs

**templates/**
- Purpose: HTML dashboard templates
- Contains: Dashboard HTML files
- Key files:
  - `templates/dashboard.html`: Main strategy dashboard
  - `templates/live_trading_dashboard.html`: Live trading monitor

**data/**
- Purpose: Runtime generated data and database
- Contains: SQLite DB, reports, market data cache
- Key files:
  - `data/strategies.db`: Main database
  - `data/converted/`: Python strategy files
  - `data/market_data/`: Cached OHLCV data
  - Generated: Yes (runtime)
  - Committed: No (.gitignore)

**logs/**
- Purpose: Application logs
- Contains: API logs, pipeline logs, trade logs
- Key files:
  - `logs/api.log`: API server logs
  - `logs/api.json.log`: Structured JSON logs
  - `logs/trades/`: Trade execution logs
  - Generated: Yes (runtime)
  - Committed: No (.gitignore)

## Key File Locations

**Entry Points:**
- `main.py`: Main pipeline orchestrator (445 lines)
- `api/server.py`: FastAPI REST server (1095 lines)
- `scripts/auto_collector_service.py`: Auto-collection service (28KB)

**Configuration:**
- `.env`: Environment variables (API keys, DB path)
- `src/config.py`: Configuration class using pydantic-settings
- `docker-compose.yml`: Production deployment config

**Core Logic:**
- `src/analyzer/scorer.py`: Strategy scoring algorithm
- `src/converter/rule_based_converter.py`: Pine → Python conversion
- `src/storage/database.py`: Database operations (aiosqlite)
- `src/backtester/vectorbt_engine.py`: Backtesting engine

**Testing:**
- `tests/conftest.py`: Pytest fixtures and shared setup
- `tests/test_*.py`: Individual module tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `pine_parser.py`, `live_safeguards.py`)
- Scripts: `snake_case.py` with verb prefix (e.g., `run_collector.py`, `generate_report.py`)
- Config files: `kebab-case` or `snake_case` (e.g., `docker-compose.yml`, `.env.example`)
- HTML templates: `snake_case.html` (e.g., `live_trading_dashboard.html`)

**Directories:**
- All lowercase, underscores for multi-word (e.g., `platform_integration/`)

**Classes:**
- PascalCase (e.g., `StrategyScorer`, `PineParser`, `VectorBTEngine`)

**Functions:**
- snake_case (e.g., `save_strategy()`, `score_strategy()`, `get_db()`)

**Variables:**
- snake_case (e.g., `script_id`, `total_score`, `pine_code`)

**Constants:**
- UPPERCASE_WITH_UNDERSCORES (e.g., `API_SECRET_KEY`, `LOG_DIR`, `DB_PATH`)

## Where to Add New Code

**New Feature:**
- Primary code: Add module to appropriate `src/` subdirectory
  - Analysis feature → `src/analyzer/`
  - Conversion feature → `src/converter/`
  - Trading feature → `src/trading/`
- Tests: `tests/test_{module_name}.py`

**New API Endpoint:**
- Implementation: Add route function to `api/server.py`
- Models: Add Pydantic models in same file (before endpoint definition)
- Documentation: Auto-generated via FastAPI (`/api/docs`)

**New Strategy Analyzer:**
- Rule-based: `src/analyzer/rule_based/{feature}_detector.py`
- LLM-based: `src/analyzer/llm/{feature}_analyzer.py`
- Integration: Update `src/analyzer/scorer.py` to include new check
- Tests: `tests/test_{feature}_detector.py`

**New Conversion Logic:**
- AST node: Add to `src/converter/pine_parser.py`
- Translator: Update `src/converter/node_translator.py`
- Templates: Add to `src/converter/template_manager.py`
- Tests: `tests/test_strategy_generator.py`

**Utilities:**
- Shared helpers: `src/{module}/utils.py` (per-module utilities)
- Scripts: `scripts/{action}_{target}.py` (e.g., `quick_collect.py`)

## Special Directories

**.github/workflows/**
- Purpose: GitHub Actions CI/CD pipelines
- Generated: No (version controlled)
- Committed: Yes
- Files: `deploy.yml` (auto-deployment to Hetzner)

**.planning/codebase/**
- Purpose: GSD codebase mapping documents
- Generated: Yes (by GSD mapper)
- Committed: Yes
- Files: This document (STRUCTURE.md), ARCHITECTURE.md

**.pytest_cache/**
- Purpose: Pytest cache for faster re-runs
- Generated: Yes (runtime)
- Committed: No

**__pycache__/**
- Purpose: Python bytecode cache
- Generated: Yes (runtime)
- Committed: No

**.vscode/**
- Purpose: VSCode editor settings
- Generated: Manually
- Committed: Optional (project-specific settings)

**.claude/**
- Purpose: Claude Code skills
- Generated: Manually
- Committed: Yes

---

*Structure analysis: 2026-01-19*
