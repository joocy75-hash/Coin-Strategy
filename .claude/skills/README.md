# Skill 파일 인덱스

> **작업 시작 전 필수**: 해당 모듈 작업 시 관련 Skill 파일을 먼저 읽으세요!
>
> **작업 완료 후 필수**: Skill 파일을 최신 상태로 업데이트하세요!

---

## 📚 모듈별 Skill 파일

| 작업 영역 | Skill 파일 | 설명 |
|----------|-----------|------|
| **수집 모듈** | [collector_guide.md](collector_guide.md) | TradingView 스크래핑, Pine 코드 추출 |
| **분석 모듈** | [analyzer_guide.md](analyzer_guide.md) | Repainting, Overfitting, LLM 분석 |
| **변환 모듈** | [converter_guide.md](converter_guide.md) | Pine → Python 변환 |
| **AI 에이전트** | [agent_guide.md](agent_guide.md) | 4개 전문 에이전트 사용법 |
| **백테스트** | [backtest_guide.md](backtest_guide.md) | 백테스트 엔진, 성과 지표 |
| **파이프라인** | [pipeline_guide.md](pipeline_guide.md) | 6단계 자동화 워크플로우 |
| **배포/운영** | [deployment_guide.md](deployment_guide.md) | 서버 배포, systemd, API |

---

## 🔄 사용 방법

### 1. 작업 시작 전

```bash
# 예: Collector 모듈 작업 시작
1. Work.md 확인 → 전체 로드맵 파악
2. STATUS.md 확인 → 현재 시스템 상태
3. HANDOVER.md 확인 → 이전 작업자 인수인계 사항
4. collector_guide.md 확인 → 모듈 사용법 및 주의사항
```

### 2. 작업 진행 중

- Skill 파일의 예제 코드 참조
- 알려진 이슈 확인
- 기존 API 준수

### 3. 작업 완료 후

```bash
# 필수: 다음 3가지 업데이트
1. Skill 파일 업데이트 (새로운 함수/변경사항 기록)
2. HANDOVER.md에 인수인계 작성
3. Work.md 또는 STATUS.md 업데이트 (필요 시)
```

---

## ✅ Skill 파일 업데이트 체크리스트

작업 완료 후 다음을 확인하세요:

- [ ] 새로운 함수/클래스 추가 → 사용 예제 작성
- [ ] API 변경 → Breaking changes 명시
- [ ] 버그 수정 → "알려진 이슈" 섹션 업데이트
- [ ] 성능 개선 → 개선 전후 비교 기록
- [ ] "변경 이력" 테이블에 날짜, 버전, 변경 내용 추가

---

## 📝 Skill 파일 작성 가이드

### 기본 구조

```markdown
# [모듈명] 가이드

> **모듈 위치**: `경로`
> **목적**: 간단한 설명
> **마지막 업데이트**: 날짜

---

## 📁 모듈 구조
(파일 트리)

---

## 🔧 주요 클래스 및 함수
(사용 예제 코드)

---

## 🚨 알려진 이슈
(이슈와 해결 방법)

---

## 🔄 변경 이력
(날짜, 버전, 변경 내용 테이블)

---

## ✅ 작업 시 체크리스트
```

---

## 🎯 Skill 파일의 목적

1. **온보딩 가속화**: 새 작업자가 모듈을 빠르게 이해
2. **API 문서화**: 함수 사용법 및 예제 코드 제공
3. **이슈 공유**: 알려진 문제와 해결 방법 기록
4. **변경 추적**: 코드 변경 이력 관리

---

**중요**: Skill 파일은 "살아있는 문서"입니다. 코드가 변경되면 반드시 업데이트하세요!
