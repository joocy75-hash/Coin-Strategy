# HTML 리포트 생성 기능

TradingView Strategy Research Lab의 분석 결과를 시각적으로 확인할 수 있는 HTML 리포트 생성 도구입니다.

## 주요 기능

### 1. 단일 HTML 파일
- 서버 없이 브라우저에서 바로 열 수 있는 독립 실행형 HTML 파일
- 모든 CSS와 JavaScript가 포함되어 있어 어디서든 실행 가능

### 2. 대시보드
- **통계 카드**: 총 전략 수, 분석 완료, 통과 전략, 평균 점수
- **필터링**: 검색, 등급, 상태, 최소 점수로 전략 필터링
- **정렬**: 전략명, 작성자, 좋아요, 점수, 등급, 상태별 정렬

### 3. 전략 목록 테이블
- 전략명, 작성자, 좋아요 수
- 총점, 등급 (A~F), 상태 (passed/review/rejected)
- 리페인팅 점수 (시각적 바)
- 오버피팅 점수 (시각적 바)

### 4. 상세 모달
각 전략을 클릭하면 상세 정보 표시:
- **기본 정보**: 등급, 상태, 리페인팅/오버피팅 점수
- **리페인팅 분석**: 위험 수준, 발견된 문제
- **오버피팅 분석**: 위험 수준, 파라미터 수, 우려사항
- **Pine Script 코드**: 원본 코드 (복사 버튼 포함)
- **변환된 Python 코드**: 파일 경로 정보

### 5. 다크 테마 UI
- GitHub 스타일의 현대적인 다크 테마
- 반응형 디자인 (모바일/태블릿/데스크톱)
- 부드러운 애니메이션과 인터랙션

## 사용 방법

### 기본 사용

```bash
# 리포트 생성
python scripts/generate_report.py

# 생성된 리포트 열기
python scripts/view_report.py

# 또는 직접 열기
open data/report.html
```

### 옵션

```bash
# 커스텀 데이터베이스 경로
python scripts/generate_report.py --db path/to/strategies.db

# 커스텀 출력 경로
python scripts/generate_report.py --output path/to/report.html

# 디버그 모드
python scripts/generate_report.py --debug
```

### 파이프라인 자동 생성

`main.py` 파이프라인을 실행하면 자동으로 리포트가 생성됩니다:

```bash
python main.py
```

파이프라인이 완료되면 다음 위치에 리포트가 생성됩니다:
- `data/report.html`

## 파일 구조

```
scripts/
├── generate_report.py    # 리포트 생성 스크립트
├── view_report.py         # 리포트 열기 헬퍼
└── REPORT_README.md       # 이 파일

data/
└── report.html            # 생성된 리포트
```

## 기술 스택

- **Python**: 데이터 조회 및 템플릿 렌더링
- **Jinja2**: HTML 템플릿 엔진
- **SQLite**: 데이터베이스 조회 (aiosqlite)
- **Vanilla JavaScript**: 클라이언트 사이드 인터랙션
- **CSS3**: 스타일링 및 애니메이션

## 브라우저 호환성

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## 개발자 가이드

### 템플릿 수정

`scripts/generate_report.py`의 `HTML_TEMPLATE` 변수를 수정하여 템플릿을 커스터마이징할 수 있습니다.

### 데이터 구조

리포트는 다음 데이터를 표시합니다:

```python
{
    "script_id": str,
    "title": str,
    "author": str,
    "likes": int,
    "score": float,         # 총점 (0-100)
    "grade": str,           # A, B, C, D, F
    "status": str,          # passed, review, rejected
    "repainting_score": float,
    "overfitting_score": float,
    "pine_code": str,
    "analysis": dict        # 상세 분석 결과
}
```

## 트러블슈팅

### 리포트가 비어있음
- 데이터베이스에 분석 완료된 전략이 있는지 확인
- `python main.py`를 먼저 실행하여 데이터 수집 및 분석

### JavaScript 오류
- 브라우저 콘솔에서 오류 확인
- 최신 브라우저 사용 권장

### 스타일이 깨짐
- HTML 파일을 직접 열어야 함 (file:// 프로토콜)
- 웹 서버를 통해 열 경우 CORS 이슈 없음

## 향후 개선 사항

- [ ] PDF 내보내기 기능
- [ ] 차트 및 그래프 추가
- [ ] 전략 비교 기능
- [ ] 북마크/즐겨찾기 기능
- [ ] 커스텀 테마 지원

## 라이선스

이 프로젝트의 라이선스를 따릅니다.
