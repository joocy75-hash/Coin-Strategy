# 🚨 배포 규칙 (Deployment Rules)

**작성일**: 2026-01-04
**목적**: 코드 동기화 문제 방지

---

## ⚠️ 절대 원칙

### ❌ 절대 하지 말아야 할 것

1. **원격 서버에서 직접 코드 수정**
   ```bash
   # ❌ 이렇게 하지 마세요!
   ssh root@5.161.112.248
   cd /root/service_c/strategy-research-lab
   nano src/config.py  # 절대 금지!
   ```

2. **로컬과 원격 서버의 코드가 달라지는 상황**
   - 원격에서만 수정하면 Git 이력에 없음
   - 다음 배포 시 변경사항 덮어쓰기됨
   - 코드 추적 불가능

3. **GitHub를 거치지 않는 직접 배포**
   ```bash
   # ❌ 이렇게 하지 마세요!
   scp local_file.py root@5.161.112.248:/path/
   ```

---

## ✅ 반드시 따라야 할 절차

### 표준 배포 플로우

```
┌─────────────┐
│  로컬 수정   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Git 커밋    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ GitHub 푸시  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│GitHub Actions│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  원격 배포   │
└─────────────┘
```

### 1단계: 로컬에서만 수정

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# VS Code, PyCharm 등 에디터로 코드 수정
# 예: src/config.py 수정
```

### 2단계: Git 커밋

```bash
# 변경사항 확인
git status
git diff

# 스테이징
git add .

# 의미 있는 커밋 메시지 작성
git commit -m "Fix: 버그 설명

상세 내용...

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### 3단계: GitHub 푸시

```bash
# origin/main에 푸시
git push origin main
```

### 4단계: GitHub Actions 자동 배포 (자동)

푸시하면 자동으로:
1. ✅ 코드 전송 (rsync)
2. ✅ .env 생성
3. ✅ Docker 빌드
4. ✅ 컨테이너 재시작
5. ✅ 헬스체크

### 5단계: 배포 확인

```bash
# 워크플로우 상태
gh run watch

# API 테스트
curl http://5.161.112.248:8081/api/health

# 로그 확인
ssh root@5.161.112.248 "docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs --tail=50"
```

---

## 🚨 긴급 상황 대응

### 상황: 원격 서버에서 긴급 수정이 필요한 경우

**예**: 프로덕션 장애로 즉시 수정 필요

#### 절차

1. **원격에서 임시 수정** (최소한으로)
   ```bash
   ssh root@5.161.112.248
   cd /root/service_c/strategy-research-lab
   nano src/config.py  # 긴급 수정
   docker compose restart
   ```

2. **즉시 로컬에 반영** (30분 이내)
   ```bash
   # 수정된 파일 로컬로 복사
   scp root@5.161.112.248:/root/service_c/strategy-research-lab/src/config.py \
       /Users/mr.joo/Desktop/전략연구소/strategy-research-lab/src/config.py

   # 로컬에서 커밋
   cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
   git add src/config.py
   git commit -m "Emergency fix: config.py 긴급 수정 (원격에서 먼저 적용됨)"
   git push origin main
   ```

3. **원격 서버 상태 확인**
   ```bash
   # GitHub Actions가 다시 배포하므로
   # 원격 서버가 최신 상태인지 확인
   ssh root@5.161.112.248 "cd /root/service_c/strategy-research-lab && git log -1"
   ```

---

## 🔍 동기화 상태 확인

### 주기적 점검 (주 1회 권장)

```bash
# 1. 로컬 최신 커밋
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
LOCAL_COMMIT=$(git log -1 --format="%H %s")
echo "로컬: $LOCAL_COMMIT"

# 2. GitHub 최신 커밋
GITHUB_COMMIT=$(git ls-remote origin main | awk '{print $1}')
echo "GitHub: $GITHUB_COMMIT"

# 3. 원격 서버 파일 날짜 확인
ssh root@5.161.112.248 "ls -lt /root/service_c/strategy-research-lab/src/*.py | head -5"
```

### 불일치 발견 시

**로컬 ≠ GitHub**:
```bash
# 푸시되지 않은 커밋 확인
git log origin/main..HEAD

# 푸시
git push origin main
```

**GitHub ≠ 원격 서버**:
```bash
# GitHub Actions 재실행
gh run rerun $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
```

---

## 📋 체크리스트

### 배포 전 체크리스트

- [ ] 로컬에서 코드 수정 완료
- [ ] 로컬에서 테스트 실행 (`pytest`, 수동 테스트)
- [ ] Git 상태 확인 (`git status`)
- [ ] 의미 있는 커밋 메시지 작성
- [ ] GitHub 푸시 (`git push origin main`)

### 배포 후 체크리스트

- [ ] GitHub Actions 워크플로우 성공 확인
- [ ] API 헬스체크 통과 (`curl http://5.161.112.248:8081/api/health`)
- [ ] 컨테이너 정상 실행 (`docker compose ps`)
- [ ] 로그에 오류 없음 (`docker compose logs`)
- [ ] 주요 기능 테스트 (API 호출, 수집기 동작)

---

## 🛡️ 코드 보호 전략

### 1. GitHub를 Single Source of Truth로

- 모든 코드 변경은 Git 이력으로 추적
- 언제든지 이전 버전으로 롤백 가능
- 협업 시 충돌 방지

### 2. 원격 서버는 "읽기 전용" 취급

- 원격 서버 = 배포 환경
- 수정은 항상 로컬에서
- 원격은 자동 배포 대상

### 3. CI/CD 자동화 활용

- 수동 배포 최소화
- GitHub Actions로 일관된 배포
- 배포 실패 시 자동 롤백

---

## ⚡ 빠른 참조

### 일반 배포

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
git add .
git commit -m "메시지"
git push origin main
gh run watch
```

### 긴급 수정 (원격 → 로컬 동기화)

```bash
scp root@5.161.112.248:/root/service_c/strategy-research-lab/FILE \
    /Users/mr.joo/Desktop/전략연구소/strategy-research-lab/FILE
git add FILE
git commit -m "Emergency fix"
git push origin main
```

### 동기화 확인

```bash
# 로컬 vs GitHub
git status
git log origin/main..HEAD

# GitHub Actions 상태
gh run list --limit 5
```

---

## 📞 문의

문제 발생 시:
1. 이 문서 다시 읽기
2. [핵심.md](../핵심.md) 트러블슈팅 섹션 확인
3. GitHub Issues 생성

---

**작성**: Claude Sonnet 4.5
**최종 업데이트**: 2026-01-04
**버전**: 1.0
