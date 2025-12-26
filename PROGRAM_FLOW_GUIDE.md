# 🔬 TradingView Strategy Research Lab - 상세 구동 방식

## 1. 프로젝트 개요

이 프로젝트는 TradingView에서 트레이딩 전략을 자동으로 수집, 분석, 평가하는 시스템입니다.

- **핵심 목적**: 오픈소스 Pine Script 전략의 품질을 자동화된 방식으로 검증
- **주요 기술**: Python 비동기 프로그래밍, Playwright 브라우저 자동화, GPT-4o LLM 분석

---

## 2. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    TradingView 웹사이트                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  [1단계] COLLECTOR - 전략 메타데이터 수집                          │
│  - Playwright로 브라우저 자동화                                   │
│  - 좋아요 수, 오픈소스 여부 필터링                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  [2단계] PINE FETCHER - 소스 코드 추출                            │
│  - 개별 전략 페이지 방문                                          │
│  - Pine Script 코드 추출                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  [3단계] ANALYZER - 품질 분석                                     │
│  ├─ 리페인팅 감지 (과거 신호 변경 문제)                            │
│  ├─ 오버피팅 감지 (과적합 문제)                                    │
│  ├─ 리스크 체크                                                  │
│  └─ LLM 심층 분석 (GPT-4o) [선택]                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  [4단계] CONVERTER - 코드 변환                                    │
│  - Pine Script → Python 템플릿                                   │
│  - 고득점 전략만 변환                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  [출력물]                                                        │
│  - SQLite 데이터베이스                                           │
│  - 변환된 Python 파일들                                          │
│  - HTML 대시보드 리포트                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 실행 진입점

### 3.1 메인 파일: `main.py`

```bash
# 기본 실행
python main.py

# 옵션과 함께 실행
python main.py --max-strategies 50 --min-likes 500 --skip-llm
```

### 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--max-strategies, -m` | 수집할 최대 전략 수 | 100 |
| `--min-likes, -l` | 최소 좋아요 수 필터 | 500 |
| `--sort-by, -s` | 정렬 기준 (popular/recent/trending) | popular |
| `--skip-llm` | LLM 분석 건너뛰기 | False |
| `--no-headless` | 브라우저 UI 표시 | False |
| `--analyze-limit, -a` | 분석 제한 수 | - |
| `--convert-limit, -c` | 변환 제한 수 | - |
| `--debug, -d` | 디버그 로깅 활성화 | False |

---

## 4. 단계별 상세 구동 방식

### 4.1 🔧 설정 로드 단계

**파일**: `src/config.py`

Pydantic BaseSettings를 사용한 설정 관리로, `.env` 파일에서 환경 변수를 자동 로드합니다.

```python
# 설정 로드 과정
Config 클래스 초기화
    └─→ .env 파일 읽기
    └─→ 환경 변수 오버라이드 적용
    └─→ 기본값 설정
```

**주요 설정 항목:**

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `openai_api_key` | None | GPT-4o API 키 |
| `db_path` | data/strategies.db | SQLite 데이터베이스 경로 |
| `max_strategies` | 100 | 스크래핑 제한 |
| `min_likes` | 200 | 품질 필터 |
| `headless` | True | 브라우저 모드 |
| `llm_model` | gpt-4o | LLM 모델 선택 |
| `skip_llm` | False | LLM 분석 비활성화 |
| `output_dir` | data/converted | Python 출력 디렉토리 |
| `rate_limit_delay` | 1.0 | 요청 간 지연(초) |

---

### 4.2 📡 1단계: 전략 수집 (Collection)

**파일**: `src/collector/scripts_scraper.py`

Playwright의 Async Context Manager 패턴을 사용하여 브라우저 리소스를 안전하게 관리합니다.

**동작 순서:**

```
1. Playwright Chromium 브라우저 실행
   └─→ 안티봇 감지 회피 설정 적용
   └─→ User-Agent 랜덤화
   └─→ Viewport 크기 랜덤화

2. TradingView Scripts 페이지 이동
   └─→ https://www.tradingview.com/scripts/

3. 필터 적용
   └─→ "Strategies" 필터 클릭
   └─→ 정렬 기준 적용 (인기순 등)

4. 페이지네이션 순회
   └─→ 각 페이지에서 전략 카드 추출
   └─→ 오픈소스 여부 확인
   └─→ 좋아요 수 필터링
   └─→ 최대 수집량 도달 시 종료

5. StrategyMeta 객체 리스트 반환
```

**CSS 선택자 (2024년 12월 기준):**

```python
# 전략 카드: article 태그
# 제목: a[data-qa-id="ui-lib-card-link-title"]
# 작성자: href에 /u/ 포함된 링크
# 좋아요: boost 버튼의 aria-label
```

---

### 4.3 📥 2단계: Pine 코드 추출 (Fetching)

**파일**: `src/collector/pine_fetcher.py`

TradingView UI가 자주 변경되므로 여러 선택자를 순차적으로 시도하는 다중 방법 추출 전략(Fallback Pattern)을 사용합니다.

**동작 순서:**

```
각 전략에 대해:
    │
    ├─→ 1. 전략 페이지 방문
    │
    ├─→ 2. "Source code" 버튼 클릭
    │
    ├─→ 3. 코드 추출 시도 (순차적 폴백)
    │   ├─→ Monaco 에디터 선택자
    │   ├─→ codeContainer 클래스
    │   ├─→ 구버전 위젯 선택자
    │   ├─→ pre/code 태그
    │   └─→ 정규식으로 페이지 전체 검색
    │
    ├─→ 4. 추가 데이터 추출
    │   ├─→ Pine 버전 감지 (//@version=5)
    │   ├─→ 성능 지표 파싱
    │   ├─→ 입력 파라미터 추출
    │   └─→ 전략 설명
    │
    └─→ 5. Rate limiting (1-2초 대기)
```

**출력 데이터 구조:**

```python
@dataclass
class PineCodeData:
    script_id: str
    pine_code: str          # 추출된 Pine Script
    pine_version: int       # 버전 (4 또는 5)
    performance: dict       # 백테스트 성능
    inputs: list            # 입력 파라미터들
    description: str        # 전략 설명
```

---

### 4.4 🔍 3단계: 품질 분석 (Analysis)

**파일**: `src/analyzer/scorer.py`

여러 분석 결과를 가중치 기반으로 종합하여 단일 점수를 계산합니다.

**점수 가중치:**

| 분석 항목 | 가중치 | 설명 |
|----------|--------|------|
| 리페인팅 안전성 | 25% | 과거 신호가 변경되지 않는지 |
| 오버피팅 위험 | 25% | 과적합 가능성 |
| 리스크 관리 | 20% | 손절/익절 설정 |
| LLM 심층 분석 | 30% | GPT-4o 종합 평가 |

**등급 기준:**

| 등급 | 점수 범위 |
|------|----------|
| A | ≥ 85 |
| B | ≥ 70 |
| C | ≥ 55 |
| D | ≥ 40 |
| F | < 40 |

**상태 결정:**

- `passed`: 점수 ≥ 60, 낮은 위험
- `review`: 40-60, 검증 필요
- `rejected`: < 40 또는 치명적 문제 (CRITICAL 리페인팅)

#### 4.4.1 리페인팅 감지

**파일**: `src/analyzer/rule_based/repainting_detector.py`

리페인팅이란 백테스트에서는 완벽한 신호를 보이지만, 실제 거래에서는 신호가 바뀌는 현상입니다.

**위험도 레벨:**

| 레벨 | 패턴 예시 | 점수 |
|------|----------|------|
| CRITICAL | `barmerge.lookahead_on` | 0점 (즉시 거부) |
| HIGH | `close` 직접 사용, `barstate.isrealtime` | 25점 |
| MEDIUM | `security()` lookahead 미지정 | 50점 |
| LOW | 일부 의심 패턴 | 75점 |
| SAFE | `barstate.isconfirmed`, `[1]` 참조 | 보너스 |

**CRITICAL 패턴 (즉시 거부):**
- `barmerge.lookahead_on`: 직접적인 미래 데이터 사용
- `request.security` with lookahead_on

**HIGH 위험 패턴:**
- 직접적인 `close` 사용 (현재 미확정 봉)
- `barstate.isrealtime` 의존
- `barstate.isconfirmed == false` 신호
- `security()[0]` (다른 타임프레임의 현재 봉)

**SAFE 패턴 (보너스):**
- `barstate.isconfirmed == true` 확인
- `[1]` 이전 봉 참조
- `lookahead_off` 명시적 사용

#### 4.4.2 오버피팅 감지

**파일**: `src/analyzer/rule_based/overfitting_detector.py`

**검사 항목:**

```
1. 파라미터 개수 분석
   └─→ ≤5개: 안전
   └─→ 6-10개: 주의
   └─→ 11-15개: 위험
   └─→ ≥20개: 심각

2. 매직 넘버 탐지
   └─→ 로직 없이 하드코딩된 숫자들

3. 하드코딩된 날짜
   └─→ 특정 기간에만 최적화된 전략

4. 비현실적 성능
   └─→ 승률 > 85%
   └─→ Profit Factor > 10
```

**위험도 레벨:**
- critical: 점수 ≥ 70
- high: 점수 50-69
- medium: 점수 30-49
- low: 점수 < 30

#### 4.4.3 리스크 체커

**파일**: `src/analyzer/rule_based/risk_checker.py`

- 포지션 사이징 로직 평가
- 손절매/익절매 구현 확인
- 레버리지 남용 감지
- 거래 빈도 관리 분석

#### 4.4.4 LLM 심층 분석 (선택사항)

**파일**: `src/analyzer/llm/deep_analyzer.py`

GPT-4o를 사용한 정성적 전략 평가입니다.

```
GPT-4o API 호출
    │
    ├─→ 전략 코드 전송 (최대 6000자)
    │
    ├─→ 분석 요청 프롬프트
    │
    └─→ JSON 응답 파싱
        ├─→ logic_score (1-10): 시장 원리 부합도
        ├─→ risk_score (1-10): 리스크 관리 품질
        ├─→ practical_score (1-10): 실거래 적합성
        └─→ code_quality_score (1-10): 코드 품질
```

**최종 점수 계산:**

```python
total = (logic × 2.5) + (risk × 2.5) + (practical × 2.5) + (code_quality × 2.5)
```

---

### 4.5 💾 데이터 저장

**파일**: `src/storage/database.py`

aiosqlite를 사용한 비동기 데이터베이스로, I/O 작업 중에도 다른 작업 수행이 가능합니다.

**데이터베이스 스키마:**

```sql
CREATE TABLE strategies (
    script_id TEXT PRIMARY KEY,
    title TEXT,
    author TEXT,
    likes INTEGER,
    views INTEGER,
    pine_code TEXT,
    pine_version INTEGER,
    performance_json TEXT,   -- JSON 직렬화
    analysis_json TEXT,      -- JSON 직렬화
    script_url TEXT,
    description TEXT,
    is_open_source BOOLEAN,
    category TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 성능 최적화 인덱스
CREATE INDEX idx_likes ON strategies(likes DESC);
CREATE INDEX idx_author ON strategies(author);
CREATE INDEX idx_created_at ON strategies(created_at DESC);
```

**주요 메서드:**
- `init_db()`: 테이블 및 인덱스 생성
- `save_strategy()`: 삽입/업데이트
- `update_converted_path()`: 변환 완료 표시
- `search()`: 필터 기반 조회
- `get_stats()`: 데이터베이스 통계

---

### 4.6 🔄 4단계: 코드 변환 (Conversion)

**파일**: `src/converter/strategy_generator.py`

Jinja2 템플릿 엔진을 사용하여 표준화된 Python 클래스를 생성합니다.

**변환 규칙:**

```python
# Pine Script → Python 매핑

# 기술적 지표
ta.sma()  →  self._sma()
ta.ema()  →  self._ema()
ta.rsi()  →  self._rsi()
ta.macd() →  self._macd()

# 데이터 참조
close     →  closes[-1]
close[1]  →  closes[-2]
open      →  opens[-1]
high      →  highs[-1]
low       →  lows[-1]
volume    →  volumes[-1]

# 연산자
true      →  True
false     →  False
and       →  and
or        →  or
:=        →  =
```

**생성되는 Python 클래스 구조:**

```python
class StrategyName:
    def __init__(self, params=None, user_id=None):
        # 파라미터 초기화

    def generate_signal(self, current_price, candles, current_position):
        # 매매 신호 생성
        return {
            "action": "buy|sell|close|hold",
            "confidence": 0.0-1.0,
            "reason": "신호 발생 이유",
            "strategy_type": "전략 유형",
            "ai_powered": False
        }

    def _check_exit(self, position, current_price):
        # 청산 조건 확인
```

---

### 4.7 📊 리포트 생성

**파일**: `scripts/generate_report.py`

```
데이터베이스에서 전략 조회
    │
    └─→ Jinja2 HTML 템플릿 렌더링
        │
        ├─→ 전략 목록 테이블
        ├─→ 점수별 필터링
        ├─→ 상세 분석 결과
        └─→ 인터랙티브 차트
            │
            └─→ data/report.html 저장
```

---

## 5. 디렉토리 구조

```
strategy-research-lab/
├── main.py                     # 메인 진입점
├── .env                        # 환경 설정 (API 키 등)
├── requirements.txt            # Python 의존성
│
├── src/
│   ├── config.py              # 설정 관리
│   │
│   ├── collector/             # 데이터 수집
│   │   ├── scripts_scraper.py # TradingView 스크래핑
│   │   ├── pine_fetcher.py    # Pine 코드 추출
│   │   ├── session_manager.py # 세션/프록시 관리
│   │   ├── performance_parser.py
│   │   └── quality_scorer.py  # 사전 품질 필터링
│   │
│   ├── analyzer/              # 품질 분석
│   │   ├── scorer.py          # 점수 계산기
│   │   ├── rule_based/
│   │   │   ├── repainting_detector.py
│   │   │   ├── overfitting_detector.py
│   │   │   └── risk_checker.py
│   │   └── llm/
│   │       ├── deep_analyzer.py
│   │       └── prompts.py
│   │
│   ├── converter/             # 코드 변환
│   │   ├── strategy_generator.py
│   │   └── pine_to_python.py
│   │
│   └── storage/               # 데이터 저장
│       ├── database.py
│       ├── models.py
│       └── exporter.py
│
├── scripts/                   # 유틸리티 스크립트
│   ├── quick_collect.py       # 빠른 수집
│   ├── analyze_strategies.py  # 분석 실행
│   ├── run_collector.py       # 수집기 실행
│   ├── run_analyzer.py        # 분석기 실행
│   ├── run_converter.py       # 변환기 실행
│   ├── run_full_pipeline.py   # 전체 파이프라인
│   ├── generate_report.py     # 리포트 생성
│   ├── view_report.py         # 리포트 열기
│   └── test_report.py         # 리포트 테스트
│
├── data/                      # 출력 데이터
│   ├── strategies.db          # SQLite DB
│   ├── report.html            # HTML 리포트
│   ├── beginner_report.html   # 간소화된 리포트
│   ├── collected_*.json       # 수집 결과
│   ├── analyzed_*.json        # 분석 결과
│   ├── quality_*.json         # 품질 점수
│   └── converted/             # 변환된 Python 파일들
│       ├── {script_id}_strategy.py
│       └── ...
│
└── logs/                      # 로그 파일
```

---

## 6. 실행 예시

### 기본 실행

```bash
# 전체 파이프라인 실행
python main.py

# 50개 전략만 수집, LLM 분석 제외
python main.py --max-strategies 50 --skip-llm

# 좋아요 1000개 이상만 수집, 브라우저 표시
python main.py --min-likes 1000 --no-headless

# 디버그 모드로 최근 전략 수집
python main.py --sort-by recent --debug
```

### 개별 스크립트 실행

```bash
# 빠른 수집만
python scripts/quick_collect.py

# 수집된 전략 분석
python scripts/run_analyzer.py

# Python으로 변환
python scripts/run_converter.py

# 리포트만 생성
python scripts/generate_report.py

# 리포트 브라우저에서 열기
python scripts/view_report.py
```

### 전체 파이프라인 래퍼

```bash
python scripts/run_full_pipeline.py --max-strategies 50 --skip-llm
```

---

## 7. 데이터 흐름 요약

```
┌────────────────────────────────────────────────────────────────┐
│                        입력 소스                                │
├────────────────────────────────────────────────────────────────┤
│  • TradingView 웹사이트 (전략 목록, 개별 페이지)                  │
│  • .env 파일 (API 키, 설정값)                                   │
│  • 명령줄 인자                                                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                        처리 단계                                │
├────────────────────────────────────────────────────────────────┤
│  1. 웹 스크래핑 → 메타데이터 추출                               │
│  2. 코드 추출 → Pine Script 소스                               │
│  3. 패턴 분석 → 위험 요소 감지                                  │
│  4. LLM 분석 → 심층 평가 (선택)                                │
│  5. 점수 계산 → 가중치 적용                                    │
│  6. 코드 변환 → Python 템플릿                                  │
│  7. 리포트 생성 → HTML 시각화                                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                        출력물                                   │
├────────────────────────────────────────────────────────────────┤
│  • strategies.db - SQLite 데이터베이스                          │
│  • data/converted/*.py - 변환된 Python 전략 파일                │
│  • data/report.html - 인터랙티브 대시보드                       │
│  • data/*.json - JSON 내보내기 파일                            │
│  • logs/*.log - 실행 로그                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 8. 핵심 설계 패턴

이 프로젝트에서 사용된 주요 디자인 패턴:

1. **Async Context Manager**: 브라우저 리소스의 안전한 관리
   - `async with` 구문으로 예외 발생 시에도 브라우저 자동 종료
   - 메모리 누수 방지

2. **Strategy Pattern**: 여러 분석 방법을 교체 가능하게 설계
   - 규칙 기반 분석 (RepaintingDetector, OverfittingDetector)
   - LLM 기반 분석 (LLMDeepAnalyzer)

3. **Template Method**: Jinja2를 통한 코드 생성
   - 표준화된 Python 클래스 구조
   - 유연한 템플릿 커스터마이징

4. **Composition over Inheritance**: 독립적인 Detector 클래스들의 조합
   - 각 분석기가 독립적으로 동작
   - 새로운 분석기 추가가 용이

5. **Dependency Injection**: Config 객체를 각 컴포넌트에 주입
   - 테스트 용이성 향상
   - 설정 변경 시 코드 수정 최소화

6. **Fallback Pattern**: 다중 방법 추출 전략
   - UI 변경에 대한 견고성
   - 하나의 방법이 실패해도 다음 방법으로 시도

---

## 9. 의존성

### 핵심 라이브러리 (requirements.txt)

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| playwright | ≥ 1.40 | 브라우저 자동화 |
| pydantic | ≥ 2.5 | 데이터 검증 |
| aiosqlite | ≥ 0.19 | 비동기 SQLite |
| openai | ≥ 1.6 | GPT-4o API |
| Jinja2 | ≥ 3.1 | 템플릿 렌더링 |
| pandas | ≥ 2.1 | 데이터 처리 |
| rich | ≥ 13.7 | 콘솔 출력 |
| httpx | ≥ 0.25 | HTTP 클라이언트 |
| tenacity | ≥ 8.2 | 재시도 로직 |

### 개발 도구

- pytest, pytest-asyncio: 테스팅
- black, mypy, ruff: 코드 품질

---

## 10. 확장성 기능

- **Async/Await**: 웹 스크래핑을 위한 논블로킹 I/O
- **Rate Limiting**: 설정 가능한 지연 및 백오프
- **Proxy Support**: 분산 스크래핑을 위한 프록시 로테이션
- **Batch Processing**: 파이프라인이 전략을 순차 처리
- **SQLite with Indexing**: 효율적인 저장 및 조회
- **JSON Serialization**: 복잡한 분석 결과를 위한 유연한 스키마

---

## 11. 문제 해결

### 일반적인 문제

1. **브라우저 실행 실패**
   ```bash
   playwright install chromium
   ```

2. **OpenAI API 키 오류**
   - `.env` 파일에 `OPENAI_API_KEY` 설정 확인

3. **TradingView 접근 차단**
   - Rate limiting 증가: `RATE_LIMIT_DELAY=2.0`
   - 프록시 사용 고려

4. **메모리 부족**
   - `--max-strategies` 값 줄이기
   - 배치 처리로 분할 실행

---

## 12. 참고 자료

- [Pine Script 공식 문서](https://www.tradingview.com/pine-script-docs/)
- [Playwright Python 문서](https://playwright.dev/python/)
- [Pydantic 문서](https://docs.pydantic.dev/)
- [OpenAI API 문서](https://platform.openai.com/docs/)
