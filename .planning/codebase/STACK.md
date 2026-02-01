# Technology Stack

**Analysis Date:** 2026-01-19

## Languages

**Primary:**
- Python 3.11+ - All application code, data processing, web scraping, backtesting

**Secondary:**
- Shell (Bash) - Deployment scripts, automation
- HTML/JavaScript - Dashboard templates, data visualization

## Runtime

**Environment:**
- Python 3.11.9 (current deployment)

**Package Manager:**
- pip (Python Package Installer)
- Lockfile: Not present (uses requirements.txt only)

## Frameworks

**Core:**
- FastAPI 0.109.0+ - REST API server (`api/server.py`)
- Uvicorn 0.27.0+ - ASGI server with [standard] extras
- Playwright 1.40.0+ - Web scraping, browser automation
- Pydantic 2.5.0+ - Data validation and settings management

**Testing:**
- pytest 7.4.0+ - Test framework
- pytest-asyncio 0.23.0+ - Async test support

**Build/Dev:**
- Docker (Dockerfile multi-stage build, Python 3.11-slim base)
- Docker Compose (orchestration for multi-container deployment)
- black 23.12.0+ - Code formatting
- mypy 1.7.0+ - Type checking
- ruff 0.1.0+ - Fast linting

## Key Dependencies

**Critical:**
- anthropic 0.40.0+ - Claude AI integration for strategy analysis
- openai 1.6.0+ - GPT-4 integration for LLM analysis
- ccxt 4.2.0+ - Cryptocurrency exchange integration (backtesting)
- cryptography 42.0.0+ - API key encryption and secure storage

**Infrastructure:**
- aiosqlite 0.19.0+ - Async SQLite database operations
- aiohttp 3.9.0+ - Async HTTP client
- aiofiles 23.2.0+ - Async file I/O
- httpx 0.25.0+ - HTTP client with async support

**Data Processing:**
- numpy 1.26.0+ - Numerical computing
- pandas 2.1.0+ - Data manipulation and analysis
- pyarrow 14.0.0+ - Parquet support for caching
- vectorbt 0.26.0+ - High-speed backtesting (10-100x faster)

**Specialized:**
- pynescript 0.2.0+ - Pine Script AST-based static analysis
- transformers 4.36.0+ - FinBERT financial sentiment analysis
- torch - PyTorch backend for FinBERT
- playwright-stealth 1.0.6+ - Bot detection evasion

**Web Framework:**
- Jinja2 3.1.0+ - Template engine for HTML generation
- slowapi 0.1.9+ - Rate limiting middleware

**CLI/UX:**
- rich 13.7.0+ - Rich terminal formatting
- typer 0.9.0+ - CLI interface builder

**Utilities:**
- python-dotenv 1.0.0+ - Environment configuration
- tenacity 8.2.0+ - Retry logic with backoff
- psutil 5.9.0+ - Process and system monitoring

## Configuration

**Environment:**
- `.env` file for local configuration
- Environment variables for production secrets
- `src/config.py` uses pydantic-settings for type-safe config loading
- Key variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, DB_PATH, LLM_MODEL, HEADLESS

**Build:**
- `Dockerfile` - Multi-stage build, non-root user, Playwright Chromium installation
- `docker-compose.yml` - Service definitions for strategy-lab and scheduler containers
- Resource limits: 2 CPU cores / 2GB RAM (strategy-lab), 1.5 CPU / 1.5GB RAM (scheduler)

## Platform Requirements

**Development:**
- Python 3.10+ required (3.11+ recommended)
- Playwright browsers (Chromium with dependencies)
- 4GB+ RAM for VectorBT backtesting
- SQLite 3.0+

**Production:**
- Docker + Docker Compose deployment
- Hetzner VPS (current: 141.164.55.245)
- GitHub Actions CI/CD pipeline (`.github/workflows/deploy.yml`)
- External network: proxy-net (Docker network bridge)
- Health check endpoint: `http://localhost:8080/api/health`
- Port mapping: Host 8081 → Container 8080

---

*Stack analysis: 2026-01-19*
