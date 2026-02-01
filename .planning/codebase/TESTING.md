# Testing Patterns

**Analysis Date:** 2026-01-19

## Test Framework

**Runner:**
- pytest 7.4.0+
- Config: Not explicitly defined (uses defaults)

**Assertion Library:**
- Python built-in `assert` statements
- No additional assertion libraries detected

**Run Commands:**
```bash
pytest tests/                    # Run all tests
pytest tests/test_api.py -v      # Run specific test file with verbose
pytest -k "test_strategy" -v     # Run tests matching pattern
python -m pytest tests/          # Alternative invocation
```

**Additional Options:**
```bash
pytest --asyncio-mode=auto       # For async tests (pytest-asyncio)
python test_api.py              # Some tests have __main__ runner
```

## Test File Organization

**Location:**
- Co-located test directories: `tests/` at project root and `trading-agent-system/tests/`
- Separate from source: Tests in `tests/`, source in `src/`

**Naming:**
- Pattern: `test_*.py` (e.g., `test_api.py`, `test_strategy_generator.py`, `test_overfitting_detector.py`)
- Mirrors source names: `src/analyzer/scorer.py` → `tests/test_scorer.py`
- Descriptive suffixes for integration: `test_integration.py`, `test_opensource_integration.py`

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures
├── test_api.py                    # API endpoint tests
├── test_strategy_generator.py     # StrategyGenerator unit tests
├── test_overfitting_detector.py   # OverfittingDetector tests
├── test_repainting_detector.py    # RepaintingDetector tests
├── test_scorer.py                 # Scorer tests
└── test_integration.py            # End-to-end tests
```

## Test Structure

**Suite Organization:**
```python
class TestHealthEndpoint:
    """헬스 체크 엔드포인트 테스트"""

    def test_health_check(self, client):
        """헬스 체크 정상 응답"""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
```

**Patterns:**
- Class-based grouping: `class Test{Component}{Feature}:`
- Docstrings in Korean for business context
- Setup via `@pytest.fixture(autouse=True)` in class
- Descriptive test names: `test_{action}_{expected_outcome}`

**Common Structure:**
```python
def test_feature_name(self, fixture):
    """Test description"""
    # Arrange
    input_data = setup_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result.success == True
    assert "expected_key" in result.data
```

## Mocking

**Framework:** unittest.mock (standard library)

**Patterns:**
```python
from unittest.mock import patch, MagicMock

@patch('module.ExternalService')
def test_with_mock(mock_service):
    mock_service.return_value = expected_value
    # test code
```

**What to Mock:**
- External API calls (OpenAI, Anthropic, Binance)
- Database connections in isolation tests
- File system operations
- Network requests
- LLM API responses

**What NOT to Mock:**
- Core business logic (analyzers, detectors)
- Data structures (dataclasses, Pydantic models)
- Simple utilities
- Configuration loading

**Mock Examples:**
- Environment variables: `os.environ["API_SECRET_KEY"] = "test_secret_key"`
- Database: `db_path=":memory:"` for in-memory SQLite tests
- Fixtures provide mock data rather than mocking the entire object

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def sample_pine_script_safe():
    """리페인팅 위험이 없는 안전한 Pine Script"""
    return '''
//@version=5
strategy("Safe Strategy", overlay=true)

// 이전 봉 데이터만 사용
fast_ma = ta.sma(close[1], 10)
slow_ma = ta.sma(close[1], 20)

if barstate.isconfirmed
    if ta.crossover(fast_ma, slow_ma)
        strategy.entry("Long", strategy.long)
'''
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Module-specific fixtures: Within test files as `@pytest.fixture`

**Fixture Types:**
- Sample Pine scripts: `sample_pine_script_safe`, `sample_pine_script_repainting`, `sample_pine_script_overfitting`
- Mock metadata: `mock_strategy_meta`, `mock_performance_good`, `mock_performance_suspicious`
- Test clients: `client` fixture returns FastAPI TestClient
- Temp paths: `temp_db_path(tmp_path)` for isolated database tests
- Config fixtures: `test_config` returns Config with test settings

**Fixture Scope:**
- Default (function scope) for most fixtures
- No session or module-scoped fixtures detected

## Coverage

**Requirements:** None enforced

**Coverage Tool:**
- Not configured in requirements.txt or pytest config
- No coverage reports found

**View Coverage:**
```bash
# Not currently configured
# Would typically use:
pytest --cov=src --cov-report=html tests/
```

## Test Types

**Unit Tests:**
- Scope: Single function or class method
- Approach: Test in isolation with mocks for dependencies
- Examples:
  - `test_normalize_code_lowercase()` - Tests `_normalize_code()` method
  - `test_detect_pine_version_5()` - Tests version detection
  - `test_repainting_analysis()` - Tests RepaintingDetector logic

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Real database (in-memory), real data structures, mocked external APIs
- Examples:
  - `test_api.py` - Tests FastAPI endpoints with TestClient
  - `test_integration.py` - End-to-end workflow tests
  - `test_opensource_integration.py` - Tests third-party library integration

**E2E Tests:**
- Framework: Not extensively used
- Playwright available (for web scraping tests)
- Pattern: Scripts like `test_scraper.py`, `test_connection.py` can be run standalone

## Common Patterns

**Async Testing:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await async_function()
    assert result is not None
```

**Requires:** pytest-asyncio 0.23.0+

**Error Testing:**
```python
def test_validation_error(self):
    """잘못된 입력 시 에러 발생"""
    with pytest.raises(HTTPException) as exc_info:
        validate_script_id("invalid<>id")

    assert exc_info.value.status_code == 400
    assert "Invalid" in str(exc_info.value.detail)
```

**API Endpoint Testing:**
```python
def test_endpoint(self, client):
    """API 엔드포인트 테스트"""
    response = client.get("/api/endpoint")
    assert response.status_code == 200

    data = response.json()
    assert "expected_field" in data
```

**Parametrized Tests:**
```python
# Not extensively used, but available via pytest
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
def test_with_params(input, expected):
    assert process(input) == expected
```

**Database Testing:**
```python
def test_with_db(temp_db_path):
    """임시 데이터베이스 사용"""
    conn = sqlite3.connect(temp_db_path)
    # test database operations
    conn.close()
```

**Compilation Testing:**
```python
def test_generated_code_is_valid(self, sample_pine_script):
    """생성된 Python 코드가 유효한지 검증"""
    result = generator.generate_strategy(...)

    try:
        compile(result["strategy_file"], "<string>", "exec")
        compiled = True
    except SyntaxError:
        compiled = False

    assert compiled, "Generated code should be valid Python"
```

## Test Data Patterns

**Realistic Test Data:**
- Full Pine Script examples in fixtures
- Complete performance metrics: `profit_factor`, `win_rate`, `max_drawdown`
- Multi-scenario coverage: safe vs. repainting vs. overfitting scripts

**Edge Cases:**
```python
def test_empty_input_returns_default(self):
    """빈 문자열은 기본값 반환"""
    result = self.generator._normalize_code("")
    assert result == "custom_strategy"
```

**Boundary Testing:**
```python
def test_strategies_invalid_limit(self, client):
    """잘못된 limit 파라미터"""
    response = client.get("/api/strategies?limit=500")
    assert response.status_code == 422  # Validation error
```

## Test Execution Pattern

**Main Runner in Test Files:**
```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Allows running individual test files directly:
```bash
python tests/test_api.py
```

## Security Testing

**Input Sanitization:**
```python
def test_search_sanitization(self, client):
    """검색어 sanitization"""
    # SQL Injection 시도
    response = client.get("/api/strategies?search='; DROP TABLE strategies; --")
    assert response.status_code == 200  # 에러 없이 처리

def test_xss_prevention(self, client):
    """XSS 방지"""
    response = client.get("/api/strategies?search=<script>alert(1)</script>")
    assert response.status_code == 200
```

## Test Organization Best Practices

**Grouping:**
- Related tests in classes
- One test file per module/component
- Shared setup in fixtures

**Naming:**
- Test methods start with `test_`
- Descriptive: `test_{what}_{condition}_{expected}`
- Korean docstrings for context

**Assertions:**
- Multiple assertions per test acceptable
- Assert both positive and negative cases
- Check response structure, not just success

---

*Testing analysis: 2026-01-19*
