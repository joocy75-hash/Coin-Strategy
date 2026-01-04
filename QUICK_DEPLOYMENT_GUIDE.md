# 🚀 빠른 배포 가이드 (Quick Deployment Guide)

**목적**: 1분 안에 원격 서버 배포 완료하기

---

## ⚠️ 코드 동기화 원칙 (필독!)

### 절대 원칙

**❌ 절대 하지 말 것**:
- 원격 서버에서 직접 코드 수정
- 로컬과 원격의 코드가 달라지는 상황
- GitHub를 거치지 않는 배포

**✅ 반드시 따를 것**:
1. 모든 코드 수정은 **로컬에서만**
2. 수정 후 **반드시 GitHub 푸시**
3. GitHub Actions가 **자동 배포**

### 배포 플로우

```
로컬 수정 → Git 푸시 → GitHub Actions → 원격 서버
```

이 순서를 **절대 어기지 마세요!**

---

## ⚡ 즉시 배포 (자동화)

```bash
# 현재 위치에서 실행
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# GitHub에 푸시 (자동 배포 트리거)
git add .
git commit -m "Deploy to production server"
git push origin main
```

**완료!** GitHub Actions가 자동으로:
1. SSH 연결 (5.161.112.248)
2. 코드 전송
3. Docker 빌드
4. 서비스 시작
5. 헬스체크

**소요 시간**: 5-10분

---

## 📊 배포 상태 확인

```bash
# GitHub Actions 워크플로우 상태 보기
gh run list --limit 1

# 실시간 로그 보기
gh run watch

# 배포 완료 후 API 테스트
curl http://5.161.112.248:8081/api/health
curl http://5.161.112.248:8081/api/stats
```

**브라우저에서 확인**:
- API 문서: http://5.161.112.248:8081/api/docs
- 전략 리포트: http://5.161.112.248:8081/

---

## 🔍 문제 발생 시

### 1. GitHub Actions 실패
```bash
gh run view  # 로그 확인
```

**원인**: SSH 키 또는 API 키 문제
**해결**: GitHub 저장소 Settings → Secrets 확인

### 2. API 응답 없음
```bash
ssh root@5.161.112.248 "docker compose ps"
ssh root@5.161.112.248 "docker compose logs --tail=50"
```

**원인**: 컨테이너 시작 실패
**해결**: 로그에서 오류 확인 후 재시작

### 3. 수집기 작동 안 함
```bash
ssh root@5.161.112.248 "docker compose logs scheduler"
```

**원인**: ANTHROPIC_API_KEY 누락
**해결**: GitHub Secret `ANTHROPIC_API_KEY` 확인

---

## 📝 자동화 동작 방식

배포 후 **자동으로 실행되는 작업**:

1. **6시간마다**:
   - TradingView에서 전략 수집 (최소 500 부스트)
   - Pine Script 코드 추출
   - AI 품질 분석 (Claude)
   - 백테스트 실행 (BTC/USDT 1h)
   - HTML 리포트 생성

2. **실시간**:
   - API 서버 대기 (8081 포트)
   - 전략 조회/검색/필터링
   - 개별 백테스트 실행

3. **텔레그램 알림** (환경변수 설정 시):
   - 수집 시작/완료 알림
   - 상위 전략 알림
   - 오류 발생 알림

---

## 🛑 서비스 중지

```bash
ssh root@5.161.112.248 "docker compose down"
```

## 🔄 서비스 재시작

```bash
ssh root@5.161.112.248 "docker compose restart"
```

---

## 📚 추가 문서

- 상세 배포 보고서: [DEPLOYMENT_READINESS_REPORT.md](DEPLOYMENT_READINESS_REPORT.md)
- 해외 IP 안전성: [OVERSEAS_IP_POLICY.md](OVERSEAS_IP_POLICY.md)
- 작업 세션 완료: [WORK_SESSION_COMPLETE_20260104.md](WORK_SESSION_COMPLETE_20260104.md)

---

**배포 준비 상태**: ✅ **100% 완료**
**즉시 실행 가능**: ✅ **예**
