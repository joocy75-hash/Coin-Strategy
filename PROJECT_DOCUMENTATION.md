# Strategy Research Lab - 프로젝트 문서

> TradingView 트레이딩 전략 수집, 분석, 품질 평가 자동화 시스템

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [핵심 모듈 상세](#3-핵심-모듈-상세)
4. [데이터 흐름](#4-데이터-흐름)
5. [실행 방법](#5-실행-방법)
6. [분석 알고리즘](#6-분석-알고리즘)
7. [데이터 스키마](#7-데이터-스키마)
8. [현재 구현 상태](#8-현재-구현-상태)
9. [알려진 제한사항](#9-알려진-제한사항)

---

## 1. 프로젝트 개요

### 1.1 목적
TradingView에서 인기있는 트레이딩 전략을 자동으로 수집하고, Pine Script 코드를 분석하여 **품질이 좋은 전략**을 필터링하는 시스템.

### 1.2 핵심 기능
| 기능 | 설명 | 구현 상태 |
|------|------|----------|
| 전략 수집 | TradingView에서 전략 메타데이터 수집 | ✅ 완료 |
| Pine Script 추출 | 오픈소스 전략의 Pine 코드 추출 | ✅ 완료 |
| 리페인팅 탐지 | 미래 데이터 사용 패턴 탐지 | ✅ 완료 |
| 과적합 탐지 | 과도한 파라미터, 매직넘버 탐지 | ✅ 완료 |
| 품질 점수화 | 코드 40% + 성과 40% + 인기도 20% | ✅ 완료 |
| 성과 지표 파싱 | Strategy Tester 결과 파싱 | ⚠️ 부분 구현 |

### 1.3 기술 스택
```
Python 3.11+
├── playwright          # 브라우저 자동화 (TradingView 스크래핑)
├── pydantic-settings   # 설정 관리
├── dataclasses         # 데이터 모델
└── asyncio             # 비동기 처리
```

---

## 2. 시스템 아키텍처

### 2.1 디렉토리 구조
```
strategy-research-lab/
├── src/                          # 핵심 소스 코드
│   ├── collector/                # 데이터 수집 모듈
│   │   ├── scripts_scraper.py    # TradingView 스크래핑
│   │   ├── pine_fetcher.py       # Pine Script 코드 추출
│   │   ├── performance_parser.py # 성과 지표 파싱
│   │   └── session_manager.py    # 세션 관리
│   │
│   ├── analyzer/                 # 분석 모듈
│   │   ├── rule_based/           # 규칙 기반 분석
│   │   │   ├── repainting_detector.py  # 리페인팅 탐지
│   │   │   └── overfitting_detector.py # 과적합 탐지
│   │   └── llm/                  # LLM 기반 분석 (미완성)
│   │       ├── deep_analyzer.py
│   │       └── prompts.py
│   │
│   ├── converter/                # 변환 모듈 (미완성)
│   │   ├── pine_to_python.py
│   │   └── strategy_generator.py
│   │
│   ├── storage/                  # 저장 모듈
│   │   ├── database.py
│   │   ├── models.py
│   │   └── exporter.py
│   │
│   └── config.py                 # 설정 관리
│
├── scripts/                      # 실행 스크립트
│   ├── quick_collect.py          # ⭐ 빠른 전략 수집
│   ├── analyze_strategies.py     # ⭐ 전략 분석 + 점수화
│   ├── run_collector.py          # 상세 수집 (코드 포함)
│   └── run_full_pipeline.py      # 전체 파이프라인
│
├── data/                         # 수집/분석 결과
│   ├── collected_*.json          # 수집된 전략 목록
│   └── analyzed_*.json           # 분석 완료된 전략
│
└── tests/                        # 테스트 코드
```

### 2.2 모듈 의존성
```
┌─────────────────────────────────────────────────────────────┐
│                        scripts/                              │
│  quick_collect.py  →  analyze_strategies.py                 │
└─────────────────────────────────────────────────────────────┘
              │                      │
              ▼                      ▼
┌─────────────────────┐   ┌─────────────────────────────────┐
│  src/collector/     │   │  src/analyzer/rule_based/       │
│  - scripts_scraper  │   │  - repainting_detector          │
│  - pine_fetcher     │   │  - overfitting_detector         │
│  - performance_parser│   └─────────────────────────────────┘
└─────────────────────┘
              │
              ▼
┌─────────────────────┐
│  playwright         │
│  (브라우저 자동화)    │
└─────────────────────┘
```

---

## 3. 핵심 모듈 상세

### 3.1 전략 수집 (`scripts/quick_collect.py`)

**역할**: TradingView에서 오픈소스 전략 메타데이터 수집

**핵심 로직**:
```python
# 1. TradingView scripts 페이지 로드
await page.goto("https://www.tradingview.com/scripts/")

# 2. "All types" → "Strategies" 필터 적용
await page.locator('button:has-text("All types")').click()
await page.locator('text="Strategies"').click()

# 3. "Popular" 정렬 적용
await page.locator('a:has-text("Popular")').click()

# 4. "Show more publications" 버튼으로 더 많은 전략 로드
while len(strategies) < max_count:
    data = await page.evaluate(JS_EXTRACT)  # article 태그에서 추출
    show_more = page.locator('button:has-text("Show more publications")')
    await show_more.click()
```

**CSS 셀렉터** (2024년 12월 기준):
| 요소 | 셀렉터 |
|------|--------|
| 전략 카드 | `article` |
| 제목 | `a[data-qa-id="ui-lib-card-link-title"]` |
| 작성자 | `a[href*="/u/"]` |
| 좋아요 수 | `[data-qa-id="ui-lib-card-like-button"]` → `aria-label` |
| 오픈소스 여부 | `[class*="script-icon-wrap"]` → `title` 속성 |

**출력**: `data/collected_YYYYMMDD_HHMMSS.json`

---

### 3.2 전략 분석 (`scripts/analyze_strategies.py`)

**역할**: Pine Script 코드 추출 및 품질 분석

**핵심 프로세스**:
```
1. collected_*.json 로드
        │
        ▼
2. 각 전략 페이지 방문
        │
        ▼
3. "Source code" 버튼 클릭
        │
        ▼
4. Pine Script 코드 추출
   └─ document.body.innerText에서 "//@version=" 이후 추출
        │
        ▼
5. 코드 분석
   ├─ RepaintingDetector.analyze()
   └─ OverfittingDetector.analyze()
        │
        ▼
6. 점수 계산
   └─ code_score * 0.4 + performance_score * 0.4 + quality_score * 0.2
        │
        ▼
7. 결과 저장 (analyzed_*.json)
```

**Pine 코드 추출 JavaScript**:
```javascript
() => {
    const body = document.body.innerText;
    if (body.includes("//@version=")) {
        const startIdx = body.indexOf("//@version=");
        const chunk = body.slice(startIdx, startIdx + 50000);
        // "Open-source script", "Disclaimer" 등에서 종료
        return chunk.trim();
    }
    return null;
}
```

---

### 3.3 리페인팅 탐지 (`src/analyzer/rule_based/repainting_detector.py`)

**리페인팅이란?**
> 과거 캔들의 신호가 실시간으로 바뀌는 현상. 백테스트에서는 좋아 보이지만 실거래에서는 작동하지 않음.

**탐지 패턴**:

| 위험 수준 | 패턴 | 설명 |
|----------|------|------|
| CRITICAL | `lookahead=barmerge.lookahead_on` | 미래 데이터 사용 (확정적 리페인팅) |
| HIGH | `barstate.isrealtime` | 실시간 바 상태 의존 |
| HIGH | `barstate.isconfirmed == false` | 미확정 바에서 신호 |
| MEDIUM | `security()` without `lookahead` | lookahead 미명시 |
| MEDIUM | `varip` | 실시간 전용 변수 |
| MEDIUM | `timenow` | 실시간 시간 |

**안전 패턴** (가점):
- `barstate.isconfirmed == true` - 봉 완성 확인
- `[1]` - 이전 봉 데이터 사용
- `lookahead=barmerge.lookahead_off` - lookahead 명시적 비활성화

**점수 계산**:
```python
score = 100
score -= 50 if HIGH_RISK else 0
score -= 25 if MEDIUM_RISK else 0
score -= (high_count * 10) + (medium_count * 5)
score += len(safe_patterns) * 5
```

---

### 3.4 과적합 탐지 (`src/analyzer/rule_based/overfitting_detector.py`)

**과적합 징후**:
1. 과도한 파라미터 수 (최적화 과잉)
2. 매직 넘버 (특정 숫자에 과의존)
3. 특정 날짜 하드코딩 (특정 기간에 최적화)
4. 비현실적인 성과 지표

**파라미터 임계값**:
| 수준 | 파라미터 수 | 감점 |
|------|------------|------|
| Safe | ≤5 | 0 |
| Warning | 6-10 | 15 |
| Danger | 11-15 | 25 |
| Critical | >20 | 40 |

**매직 넘버 탐지**:
```python
# 3자리 이상 숫자 중 의심스러운 것
suspicious = [n for n in all_numbers
              if n not in common_values  # 100, 200, 1000 등 제외
              and not (2015 <= int(n) <= 2030)  # 년도 제외
              and int(n) % 100 != 0]  # 라운드 넘버 제외
```

**하드코딩 날짜 탐지**:
```python
patterns = [
    r'\d{4}[-/]\d{2}[-/]\d{2}',  # 2024-01-15
    r'timestamp\s*\(\s*\d{4}\s*,',  # timestamp(2024,
    r'year\s*==\s*\d{4}',  # year == 2024
]
```

---

## 4. 데이터 흐름

```
TradingView
    │
    │  Playwright (headless Chrome)
    ▼
┌─────────────────────────────────────────────────────────────┐
│  quick_collect.py                                            │
│  ───────────────                                            │
│  1. 페이지 로드: /scripts/                                   │
│  2. 필터 적용: All types → Strategies                       │
│  3. 정렬 적용: Popular                                       │
│  4. 데이터 추출: article 태그 파싱                           │
│  5. 저장: collected_YYYYMMDD_HHMMSS.json                    │
└─────────────────────────────────────────────────────────────┘
    │
    │  JSON (18개 전략)
    ▼
┌─────────────────────────────────────────────────────────────┐
│  analyze_strategies.py                                       │
│  ────────────────────                                       │
│  1. collected_*.json 로드                                   │
│  2. 각 전략 페이지 방문                                      │
│  3. "Source code" 버튼 클릭                                 │
│  4. Pine Script 추출 (body.innerText)                       │
│  5. RepaintingDetector.analyze()                            │
│  6. OverfittingDetector.analyze()                           │
│  7. 점수 계산 및 순위화                                      │
│  8. 저장: analyzed_YYYYMMDD_HHMMSS.json                     │
└─────────────────────────────────────────────────────────────┘
    │
    │  JSON (분석 완료)
    ▼
┌─────────────────────────────────────────────────────────────┐
│  분석 결과                                                   │
│  ─────────                                                  │
│  - 전략별 Pine Script 코드                                  │
│  - 리페인팅 이슈 목록                                        │
│  - 과적합 이슈 목록                                          │
│  - 종합 점수 (0-100)                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 실행 방법

### 5.1 환경 설정
```bash
cd strategy-research-lab

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install playwright pydantic-settings

# Playwright 브라우저 설치
playwright install chromium
```

### 5.2 전략 수집
```bash
# 기본 실행 (좋아요 50+, 최대 30개)
python scripts/quick_collect.py

# 커스텀 설정
python scripts/quick_collect.py --max-count 50 --min-likes 100
```

### 5.3 전략 분석
```bash
# 가장 최근 수집 파일 분석
python scripts/analyze_strategies.py

# 결과 확인
cat data/analyzed_*.json | python -m json.tool
```

### 5.4 클린 전략 필터링
```python
import json

with open('data/analyzed_YYYYMMDD_HHMMSS.json') as f:
    data = json.load(f)

# 리페인팅 이슈 없는 전략
clean = [s for s in data if not s['repainting_issues']]

# 완전 클린 전략 (리페인팅 + 과적합 없음)
perfect = [s for s in data
           if not s['repainting_issues'] and not s['overfitting_issues']]
```

---

## 6. 분석 알고리즘

### 6.1 종합 점수 계산

```python
total_score = (
    code_score * 0.4 +           # 코드 품질 (리페인팅/과적합)
    performance_score * 0.4 +    # 성과 지표
    quality_score * 0.2          # 인기도 (좋아요)
)
```

### 6.2 코드 점수 (100점 만점)

```python
code_score = 100

# 리페인팅 이슈 감점
for issue in repainting_issues:
    if issue.severity == 'high': code_score -= 30
    elif issue.severity == 'medium': code_score -= 15
    else: code_score -= 5

# 과적합 이슈 감점
for issue in overfitting_issues:
    if issue.severity == 'high': code_score -= 25
    elif issue.severity == 'medium': code_score -= 10
    else: code_score -= 5

# 코드 없으면 0점
if not pine_code: code_score = 0
```

### 6.3 인기도 점수

| 좋아요 수 | 점수 |
|----------|------|
| ≥1000 | 100 |
| ≥500 | 80 |
| ≥200 | 60 |
| ≥100 | 40 |
| <100 | 20 |

---

## 7. 데이터 스키마

### 7.1 수집 데이터 (`collected_*.json`)

```json
{
  "scriptId": "Bbh7836m-Impulsive-Trend-Detector-dtAlgo",
  "title": "Impulsive Trend Detector [dtAlgo]",
  "author": "whitebronco",
  "likes": 909,
  "href": "https://www.tradingview.com/script/Bbh7836m.../",
  "isOpenSource": true,
  "description": "This advanced Pine Script indicator..."
}
```

### 7.2 분석 데이터 (`analyzed_*.json`)

```json
{
  "script_id": "Bbh7836m-Impulsive-Trend-Detector-dtAlgo",
  "title": "Impulsive Trend Detector [dtAlgo]",
  "author": "whitebronco",
  "likes": 909,
  "script_url": "https://www.tradingview.com/script/...",

  "pine_code": "//@version=5\nindicator(\"Impulsive Trend...",
  "pine_version": 5,
  "description": "...",

  "performance": {},

  "repainting_issues": [
    {"message": "MEDIUM: security() 사용 (lookahead 미명시)", "severity": "medium"}
  ],
  "overfitting_issues": [
    {"message": "파라미터 수 주의: 12개", "severity": "medium"}
  ],

  "quality_score": 80,
  "performance_score": 50,
  "code_score": 65,
  "total_score": 62,

  "error": null
}
```

---

## 8. 현재 구현 상태

### 8.1 완료된 기능

| 기능 | 파일 | 상태 |
|------|------|------|
| TradingView 스크래핑 | `quick_collect.py` | ✅ |
| 전략 필터 (Strategies) | `quick_collect.py` | ✅ |
| 인기순 정렬 | `quick_collect.py` | ✅ |
| Pine Script 추출 | `analyze_strategies.py` | ✅ |
| 리페인팅 탐지 | `repainting_detector.py` | ✅ |
| 과적합 탐지 | `overfitting_detector.py` | ✅ |
| 점수 계산 | `analyze_strategies.py` | ✅ |

### 8.2 미완성/개선 필요

| 기능 | 파일 | 상태 | 비고 |
|------|------|------|------|
| 성과 지표 추출 | `analyze_strategies.py` | ⚠️ | Strategy Tester 결과 파싱 어려움 |
| LLM 기반 분석 | `src/analyzer/llm/` | ❌ | 구조만 존재 |
| Pine → Python 변환 | `src/converter/` | ❌ | 구조만 존재 |
| DB 저장 | `src/storage/` | ❌ | 현재 JSON만 사용 |
| 무한 스크롤 | `quick_collect.py` | ⚠️ | TradingView가 제한 |

### 8.3 최근 분석 결과 (2024-12-24)

**수집**: 18개 전략 (좋아요 50+)

**분석 결과**:
- 리페인팅 이슈 없음: **11개** (61%)
- 완전 클린 (리페인팅+과적합 없음): **2개** (11%)

**Top 3 클린 전략**:
1. **Smart Gap Concepts** (코드 100점)
2. **Kalman Hull Kijun** (코드 100점)
3. **TwinSmooth ATR Bands** (코드 95점)

---

## 9. 알려진 제한사항

### 9.1 TradingView 제한

| 제한 | 설명 | 해결책 |
|------|------|--------|
| "Show more" 버튼 소실 | 2-3회 클릭 후 버튼 사라짐 | 약 18-24개로 제한 |
| 로그인 필요 | 일부 기능은 로그인 필요 | 현재 비로그인 모드 |
| Rate Limiting | 빈번한 요청 시 차단 | 랜덤 딜레이 적용 |
| CSS 변경 | TradingView CSS 구조 자주 변경 | 정기적 셀렉터 업데이트 필요 |

### 9.2 분석 제한

| 제한 | 설명 |
|------|------|
| 성과 지표 | Strategy Tester 결과 파싱 어려움 (현재 비어있음) |
| 리페인팅 | 정적 분석이므로 100% 정확하지 않음 |
| 과적합 | 백테스트 기간/거래 수 정보 없으면 불완전 |

### 9.3 코드 추출 제한

- "Source code" 버튼 클릭 후 2초 대기 필요
- 코드가 매우 긴 경우 50KB로 제한
- 일부 protected 스크립트는 코드 없음

---

## 부록: 주요 파일 경로

```
strategy-research-lab/
├── scripts/
│   ├── quick_collect.py          # 전략 수집 (메인)
│   └── analyze_strategies.py     # 전략 분석 (메인)
│
├── src/analyzer/rule_based/
│   ├── repainting_detector.py    # 리페인팅 탐지
│   └── overfitting_detector.py   # 과적합 탐지
│
├── src/collector/
│   ├── scripts_scraper.py        # TradingView 스크래핑
│   └── performance_parser.py     # 성과 파싱
│
├── data/
│   ├── collected_*.json          # 수집 결과
│   └── analyzed_*.json           # 분석 결과
│
└── src/config.py                 # 설정
```

---

*마지막 업데이트: 2024-12-24*
