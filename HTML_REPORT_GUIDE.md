# HTML 리포트 생성 기능 사용 가이드

## 개요

TradingView Strategy Research Lab에 HTML 리포트 생성 기능이 추가되었습니다.
이 기능을 통해 분석 결과를 시각적으로 확인하고 Python 코드를 쉽게 복사할 수 있습니다.

## 빠른 시작

### 1. 리포트 생성

```bash
# 독립 실행
python scripts/generate_report.py

# 또는 전체 파이프라인 실행 (자동으로 리포트 생성됨)
python main.py
```

### 2. 리포트 열기

```bash
# 브라우저에서 자동으로 열기
python scripts/view_report.py

# 또는 수동으로 열기
open data/report.html
```

## 주요 기능

### 📊 대시보드
- 총 전략 수, 분석 완료, 통과 전략, 평균 점수 표시
- 한눈에 프로젝트 현황 파악

### 🔍 필터링 및 검색
- **검색**: 전략명이나 작성자로 빠른 검색
- **등급 필터**: A, B, C, D, F 등급별 필터
- **상태 필터**: passed, review, rejected 상태별 필터
- **점수 필터**: 최소 점수 설정

### 📋 전략 테이블
- 클릭 가능한 테이블 헤더로 정렬
- 리페인팅/오버피팅 위험도 시각화
- 색상으로 구분된 등급 및 상태 배지

### 🔬 상세 분석 모달
각 전략 클릭 시:
- 기본 정보 (등급, 상태, 점수)
- 리페인팅 분석 결과
- 오버피팅 분석 결과
- Pine Script 원본 코드 (복사 버튼 포함)
- 변환된 Python 코드 경로

### 🎨 UI/UX
- GitHub 스타일의 다크 테마
- 반응형 디자인 (모바일/태블릿/데스크톱)
- 부드러운 애니메이션

## 사용 시나리오

### 시나리오 1: 최고 점수 전략 찾기

1. 리포트 열기
2. "점수" 헤더 클릭 (자동으로 내림차순 정렬됨)
3. 상위 전략 클릭하여 상세 정보 확인
4. Pine Script 코드 복사 버튼 클릭

### 시나리오 2: 특정 작성자 전략 분석

1. 검색창에 작성자 이름 입력
2. 해당 작성자의 전략만 표시됨
3. 등급/상태 필터로 추가 필터링

### 시나리오 3: 고품질 전략만 보기

1. "등급" 필터에서 "A" 또는 "B" 선택
2. "상태" 필터에서 "통과" 선택
3. "최소 점수"에 80 입력
4. 필터링된 전략 목록 확인

## 파일 구조

```
strategy-research-lab/
├── scripts/
│   ├── generate_report.py      # 리포트 생성 스크립트
│   ├── view_report.py           # 리포트 열기 헬퍼
│   ├── test_report.py           # 테스트 스크립트
│   └── REPORT_README.md         # 상세 문서
├── data/
│   ├── strategies.db            # SQLite 데이터베이스
│   └── report.html              # 생성된 HTML 리포트
├── main.py                      # 메인 파이프라인 (리포트 자동 생성)
└── HTML_REPORT_GUIDE.md         # 이 파일
```

## 고급 사용법

### 커스텀 데이터베이스 경로

```bash
python scripts/generate_report.py --db /path/to/custom.db
```

### 커스텀 출력 경로

```bash
python scripts/generate_report.py --output /path/to/custom_report.html
```

### 디버그 모드

```bash
python scripts/generate_report.py --debug
```

## 테스트

리포트 생성 기능을 테스트하려면:

```bash
python scripts/test_report.py
```

이 스크립트는 다음을 검증합니다:
- 데이터베이스 연결
- 리포트 생성
- HTML 파일 구조
- JavaScript 기능

## 문제 해결

### 리포트가 비어 있음

**원인**: 데이터베이스에 분석된 전략이 없음

**해결**:
```bash
python main.py  # 전체 파이프라인 실행
```

### JavaScript가 작동하지 않음

**원인**: 브라우저가 오래되었거나 JavaScript가 비활성화됨

**해결**:
- 최신 브라우저 사용 (Chrome 90+, Firefox 88+, Safari 14+)
- JavaScript 활성화 확인

### 스타일이 깨짐

**원인**: CSS가 로드되지 않음

**해결**:
- HTML 파일을 직접 열기 (file:// 프로토콜)
- 웹 서버를 통해 서빙할 경우 CORS 설정 확인

## 기술적 세부사항

### 데이터 흐름

```
SQLite DB → Python (generate_report.py) → Jinja2 Template → HTML File
                                                                  ↓
                                                    Browser (JavaScript 인터랙션)
```

### 포함된 데이터

리포트는 다음 정보를 표시합니다:
- 전략 메타데이터 (제목, 작성자, 좋아요)
- 분석 결과 (점수, 등급, 상태)
- 리페인팅 분석 (위험 수준, 이슈)
- 오버피팅 분석 (위험 수준, 파라미터 수, 우려사항)
- Pine Script 원본 코드
- Python 변환 파일 경로

### 보안

- 모든 사용자 입력은 HTML 이스케이프 처리됨
- XSS 방지를 위해 textContent 사용
- 로컬 파일 시스템에서만 실행

## 향후 개선 계획

- [ ] PDF 내보내기
- [ ] 차트 및 시각화
- [ ] 전략 비교 기능
- [ ] 커스텀 테마 지원
- [ ] 성능 그래프

## 도움말

더 많은 정보는 다음 파일을 참조하세요:
- `scripts/REPORT_README.md` - 상세 개발자 문서
- `PROJECT_DOCUMENTATION.md` - 전체 프로젝트 문서

## 피드백

문제나 개선 제안이 있으시면 이슈를 등록해주세요.
