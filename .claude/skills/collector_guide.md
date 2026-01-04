# Collector 모듈 가이드

> **모듈 위치**: `strategy-research-lab/src/collector/`
>
> **목적**: TradingView에서 Pine Script 전략 자동 수집
>
> **마지막 업데이트**: 2026-01-04

---

## 📁 모듈 구조

```
src/collector/
├── __init__.py
├── scripts_scraper.py       # TradingView Scripts 페이지 크롤링
├── pine_fetcher.py          # Pine Script 코드 추출
├── performance_parser.py    # 백테스트 성과 지표 파싱
└── session_manager.py       # 세션/프록시 관리
```

---

## 🔧 주요 클래스 및 함수

### 1. TVScriptsScraper (scripts_scraper.py)

TradingView Scripts 페이지를 크롤링하여 전략 메타데이터 수집

#### 사용 예제

```python
from collector import TVScriptsScraper

scraper = TVScriptsScraper()

# 전략 수집 (최대 50개, 최소 좋아요 500)
strategies = await scraper.scrape_strategies(
    max_strategies=50,
    min_likes=500,
    sort_by="popularity"  # "popularity", "recent", "trending"
)

for strategy in strategies:
    print(f"{strategy.title} - {strategy.likes} likes")
    print(f"URL: {strategy.url}")
```

#### 주요 메서드

| 메서드 | 설명 | 파라미터 | 반환 |
|--------|------|----------|------|
| `scrape_strategies()` | 전략 목록 수집 | `max_strategies`, `min_likes`, `sort_by` | `List[StrategyMeta]` |
| `parse_strategy_card()` | 개별 전략 카드 파싱 | `card_element` | `StrategyMeta` |
| `check_open_source()` | 오픈소스 여부 확인 | `strategy_url` | `bool` |

#### 주요 설정

```python
# 스크래핑 설정
config = {
    "headless": True,           # 브라우저 헤드리스 모드
    "max_pages": 50,            # 최대 페이지 수
    "page_delay": 2.0,          # 페이지 로드 대기 시간 (초)
    "consecutive_empty": 10,    # 연속 빈 페이지 종료 기준
}
```

---

### 2. PineCodeFetcher (pine_fetcher.py)

개별 전략 페이지에서 Pine Script 코드 추출

#### 사용 예제

```python
from collector import PineCodeFetcher

fetcher = PineCodeFetcher()

# Pine 코드 추출
pine_data = await fetcher.fetch_pine_code("https://www.tradingview.com/script/abc123/")

if pine_data:
    print(f"전략명: {pine_data.title}")
    print(f"작성자: {pine_data.author}")
    print(f"코드 길이: {len(pine_data.code)} 글자")
    print(f"Pine 버전: {pine_data.pine_version}")
```

#### 주요 메서드

| 메서드 | 설명 | 파라미터 | 반환 |
|--------|------|----------|------|
| `fetch_pine_code()` | Pine 코드 추출 | `strategy_url` | `PineCodeData` |
| `extract_code_from_page()` | 페이지에서 코드 추출 | `page` | `str` |
| `detect_pine_version()` | Pine 버전 감지 | `code` | `int` (3, 4, 5) |

---

### 3. PerformanceParser (performance_parser.py)

백테스트 성과 지표 파싱

#### 사용 예제

```python
from collector import PerformanceParser

parser = PerformanceParser()

# 성과 지표 파싱
metrics = await parser.parse_performance("https://www.tradingview.com/script/abc123/")

if metrics:
    print(f"수익률: {metrics.total_return}%")
    print(f"승률: {metrics.win_rate}%")
    print(f"최대 손실폭: {metrics.max_drawdown}%")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio}")
```

---

### 4. SessionManager (session_manager.py)

세션 관리 및 차단 방지

#### 사용 예제

```python
from collector import SessionManager

session_mgr = SessionManager()

# 새 세션 생성
browser = await session_mgr.create_browser(
    headless=True,
    proxy=None  # 또는 "http://proxy:8080"
)

# User-Agent 로테이션
user_agent = session_mgr.get_random_user_agent()

# 세션 종료
await session_mgr.close_all()
```

---

## 🚨 알려진 이슈 및 해결 방법

### 이슈 1: Rate Limiting

**증상**: TradingView에서 차단되어 페이지 로드 실패

**해결 방법**:
```python
# 1. 페이지 딜레이 증가
scraper = TVScriptsScraper(page_delay=5.0)  # 기본 2초 → 5초

# 2. User-Agent 로테이션 활성화
session_mgr = SessionManager(rotate_ua=True)

# 3. 프록시 사용 (선택)
browser = await session_mgr.create_browser(proxy="http://proxy:8080")
```

### 이슈 2: 오픈소스 전략만 수집됨

**원인**: Pine 코드는 오픈소스 전략만 접근 가능

**해결 방법**:
- `check_open_source=True`로 필터링 활성화 (기본값)
- 비공개 전략은 자동 스킵됨

### 이슈 3: 연속 빈 페이지로 조기 종료

**증상**: min_likes가 높아서 대부분 페이지에서 조건 미충족

**해결 방법**:
```python
# min_likes 낮추기
strategies = await scraper.scrape_strategies(
    max_strategies=100,
    min_likes=100  # 500 → 100으로 낮춤
)
```

---

## 📊 성능 최적화

### 병렬 수집

```python
import asyncio

async def collect_multiple():
    urls = [
        "https://www.tradingview.com/script/abc123/",
        "https://www.tradingview.com/script/def456/",
        "https://www.tradingview.com/script/ghi789/",
    ]

    fetcher = PineCodeFetcher()
    tasks = [fetcher.fetch_pine_code(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [r for r in results if r and not isinstance(r, Exception)]
```

### 캐싱

```python
# 이미 수집한 전략은 DB에서 확인
from storage import StrategyDatabase

db = StrategyDatabase("data/strategies.db")

async def collect_new_only():
    scraper = TVScriptsScraper()
    strategies = await scraper.scrape_strategies(max_strategies=100)

    # DB에 없는 전략만 필터링
    new_strategies = []
    for strategy in strategies:
        if not db.exists(strategy.script_id):
            new_strategies.append(strategy)

    return new_strategies
```

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2026-01-04 | 1.0 | 초기 작성 | Claude |

---

## 📚 관련 문서

- [Work.md](../../Work.md) - 전체 로드맵
- [STATUS.md](../../strategy-research-lab/STATUS.md) - 현재 상태
- [analyzer_guide.md](analyzer_guide.md) - 다음 단계: 분석 모듈

---

## ✅ 작업 시 체크리스트

작업 완료 후 다음을 확인하세요:

- [ ] 새로운 함수 추가 시 이 파일에 사용 예제 작성
- [ ] Breaking changes 발생 시 버전 업데이트 및 변경 이력 기록
- [ ] 버그 수정 시 "알려진 이슈" 섹션 업데이트
- [ ] 성능 개선 시 벤치마크 결과 추가
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
