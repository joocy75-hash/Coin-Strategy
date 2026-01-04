# 🚀 배포 체크리스트 - TradingView Strategy Research Lab

**최종 업데이트**: 2026-01-04 21:22 KST
**대상**: 모든 작업자
**목적**: 코드 꼬임 현상 방지 및 안전한 배포

---

## ⚠️ 필독: 시작하기 전에

### 배포 3원칙

1. **로컬 우선**: 모든 코드 수정은 로컬에서만
2. **Git 필수**: 모든 변경사항은 Git 커밋
3. **자동 배포**: GitHub Actions를 통한 자동 배포

### 절대 하지 말아야 할 것

- [ ] ❌ 원격서버에 SSH 접속하여 코드 직접 수정
- [ ] ❌ Docker 컨테이너 내부에서 파일 편집
- [ ] ❌ 로컬과 원격서버 코드가 다른 상태 방치
- [ ] ❌ Git 커밋 없이 코드 수정
- [ ] ❌ `.env` 파일을 Git에 커밋

---

## 📋 작업 시작 전 체크리스트

### 1️⃣ 환경 확인

- [ ] 로컬 Python 버전 확인 (`python --version` → 3.11.14)
- [ ] Git 상태 확인 (`git status` → clean working tree)
- [ ] 최신 코드 Pull (`git pull origin main`)
- [ ] 가상환경 활성화 (`source venv/bin/activate`)

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# 환경 확인 스크립트
python --version              # Python 3.11.14 확인
git status                    # Clean working tree 확인
git pull origin main          # 최신 코드 받기
source venv/bin/activate      # 가상환경 활성화
pip list | grep anthropic     # 의존성 확인
```

### 2️⃣ 문서 확인

- [ ] [MASTER_GUIDE.md](MASTER_GUIDE.md) 읽기 (최소 1회)
- [ ] [README.md](README.md) 현재 상태 확인
- [ ] 최근 Git 커밋 확인 (`git log --oneline -5`)
- [ ] GitHub Actions 상태 확인 (`gh run list --limit 3`)

```bash
# 최근 작업 내역 확인
git log --oneline -5
git log -1 --stat

# GitHub Actions 상태
gh run list --limit 3
```

### 3️⃣ 원격서버 상태 확인

- [ ] API 헬스체크 (`curl http://5.161.112.248:8081/api/health`)
- [ ] 데이터베이스 통계 (`curl http://5.161.112.248:8081/api/stats`)
- [ ] Docker 컨테이너 상태 (SSH 접속 필요 시만)

```bash
# API 헬스체크 (로컬에서 실행)
curl -s http://5.161.112.248:8081/api/health | jq
# 예상 출력: {"status":"healthy","database_exists":true}

curl -s http://5.161.112.248:8081/api/stats | jq
# 예상 출력: {"total_strategies":44,"analyzed_count":44,...}

# (필요 시) Docker 상태 확인
ssh root@5.161.112.248 "docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps"
```

---

## 🛠️ 코드 수정 워크플로우

### Phase 1: 로컬 개발

#### 1️⃣ 브랜치 생성 (선택적, 대규모 변경 시)

```bash
# 기능 브랜치 생성 (선택)
git checkout -b feature/llm-converter
# 또는 main 브랜치에서 직접 작업 (소규모 수정)
```

#### 2️⃣ 코드 수정

```bash
# 예: analyzer 모듈 수정
vim src/analyzer/deep_analyzer.py

# 또는 VSCode
code .
```

#### 3️⃣ 로컬 테스트

- [ ] 문법 에러 확인 (`python -m py_compile src/analyzer/deep_analyzer.py`)
- [ ] 단위 테스트 실행 (`python -m pytest tests/test_analyzer.py`)
- [ ] 로컬 서버 실행 및 동작 확인

```bash
# 문법 체크
python -m py_compile src/analyzer/deep_analyzer.py

# 테스트 실행
python -m pytest tests/test_analyzer.py -v

# 로컬 API 서버 실행
python api/server.py
# 다른 터미널에서:
curl http://localhost:8080/api/health

# 수집기 단일 실행 (5개만)
python main.py --max-strategies 5
```

### Phase 2: Git 커밋

#### 4️⃣ 변경사항 확인

```bash
# 변경된 파일 목록
git status

# 변경 내용 상세 확인
git diff

# 특정 파일만 확인
git diff src/analyzer/deep_analyzer.py
```

#### 5️⃣ 스테이징 및 커밋

- [ ] 변경 파일 스테이징 (`git add`)
- [ ] 명확한 커밋 메시지 작성
- [ ] 커밋 메시지 컨벤션 준수

```bash
# 변경 파일 스테이징
git add src/analyzer/deep_analyzer.py

# 또는 모든 변경사항
git add .

# 커밋 메시지 작성 (컨벤션 준수)
git commit -m "fix: Claude API 프롬프트 개선 - Repainting 탐지 정확도 향상

- repainting_detector.py의 패턴 매칭 강화
- deep_analyzer.py의 프롬프트 구조 개선
- 테스트 케이스 3개 추가

Related: #42
"
```

**커밋 메시지 컨벤션**:
- `feat`: 새 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 기타 변경 (빌드, 설정 등)
- `perf`: 성능 개선

### Phase 3: GitHub 푸시

#### 6️⃣ 푸시 전 최종 확인

- [ ] 커밋 메시지 검토 (`git log -1`)
- [ ] `.env` 파일이 포함되지 않았는지 확인
- [ ] API 키나 비밀번호가 코드에 없는지 확인

```bash
# 커밋 내용 최종 확인
git log -1
git show HEAD

# .env 파일이 스테이징되지 않았는지 확인
git status | grep .env
# 아무 결과도 나오지 않아야 정상

# API 키 검색 (있으면 안 됨!)
git diff HEAD | grep -i "api.*key\|secret\|password"
```

#### 7️⃣ GitHub에 푸시

```bash
# main 브랜치에 푸시
git push origin main

# 또는 feature 브랜치 푸시
git push origin feature/llm-converter

# 강제 푸시는 절대 금지!
# git push --force (❌ 절대 사용 금지)
```

### Phase 4: 자동 배포 확인

#### 8️⃣ GitHub Actions 워크플로우 모니터링

- [ ] 워크플로우 시작 확인 (`gh run list`)
- [ ] 실시간 로그 확인 (`gh run watch`)
- [ ] 배포 완료 대기 (5-10분)

```bash
# 워크플로우 목록 확인
gh run list --limit 1

# 실시간 로그 확인
gh run watch

# 또는 브라우저에서 확인
open https://github.com/joocy75-hash/TradingView-Strategy/actions
```

#### 9️⃣ 배포 실패 시 대응

**실패 시 확인 사항**:
```bash
# 워크플로우 로그 확인
gh run view --log

# 일반적인 실패 원인:
# 1. SSH 키 권한 문제
# 2. 서버 접속 불가
# 3. Docker 빌드 실패
# 4. 의존성 설치 실패

# 재실행
gh run rerun <run_id>
```

### Phase 5: 배포 검증

#### 🔟 원격서버 동작 확인

- [ ] API 헬스체크 성공
- [ ] API 통계 정상 응답
- [ ] 로그 에러 없음
- [ ] 변경사항 반영 확인

```bash
# API 헬스체크
curl -s http://5.161.112.248:8081/api/health | jq

# API 통계
curl -s http://5.161.112.248:8081/api/stats | jq

# (필요 시) SSH 접속하여 로그 확인
ssh root@5.161.112.248
cd /root/service_c/strategy-research-lab

# API 서버 로그 (최근 30줄)
docker compose logs --tail=30 strategy-lab

# 스케줄러 로그 (에러만)
docker compose logs scheduler 2>&1 | grep -i error

# 변경사항 확인 (파일 해시 비교)
md5sum main.py api/server.py
```

#### 1️⃣1️⃣ 로컬 vs 원격 코드 동기화 확인

```bash
# 로컬 파일 해시
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
md5 main.py api/server.py src/analyzer/deep_analyzer.py

# 원격 파일 해시
ssh root@5.161.112.248 "cd /root/service_c/strategy-research-lab && md5sum main.py api/server.py src/analyzer/deep_analyzer.py"

# 해시가 동일해야 정상!
```

---

## 🚨 긴급 상황 대응

### 시나리오 1: 잘못된 코드를 푸시함

```bash
# 1. 이전 커밋으로 되돌리기
git log --oneline -5
# 잘못된 커밋 직전의 해시 확인

# 2. Revert (안전한 방법)
git revert <commit_hash>
git push origin main

# 3. 또는 Reset (주의 필요)
git reset --hard <good_commit_hash>
git push --force origin main  # 주의: 다른 사람과 협업 시 문제 발생 가능

# 4. GitHub Actions가 자동으로 이전 버전 배포
gh run watch
```

### 시나리오 2: 배포 후 원격서버 다운

```bash
# 1. API 응답 확인
curl http://5.161.112.248:8081/api/health
# (타임아웃 또는 Connection refused)

# 2. SSH 접속
ssh root@5.161.112.248

# 3. Docker 상태 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps
# STATUS가 "Exited"이면 문제

# 4. 로그 확인
docker compose logs strategy-lab | tail -50

# 5. 컨테이너 재시작
docker compose restart strategy-lab

# 6. 문제 지속 시 이미지 재빌드
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 시나리오 3: 로컬과 원격 코드가 다름

```bash
# 1. 해시 비교로 차이 확인
# (위의 "코드 동기화 확인" 참조)

# 2. 로컬이 최신이면 GitHub에 푸시
git push origin main

# 3. 원격이 최신이면 로컬에서 Pull
git pull origin main

# 4. 충돌 발생 시
git status
# 충돌 파일 수동 해결 후:
git add .
git commit -m "merge: resolve conflicts"
git push origin main
```

---

## 📝 배포 후 문서 업데이트

### 변경사항 기록

- [ ] MASTER_GUIDE.md 업데이트 (필요 시)
- [ ] README.md 상태 업데이트 (필요 시)
- [ ] CHANGELOG.md 작성 (새 버전 릴리즈 시)

```bash
# 문서 수정 예시
vim MASTER_GUIDE.md
# "현재 상태" 섹션 업데이트

git add MASTER_GUIDE.md
git commit -m "docs: update current status to reflect 44 strategies"
git push origin main
```

---

## ✅ 완료 체크리스트

### 모든 단계를 완료했는지 확인하세요

#### 작업 전
- [ ] 최신 코드 Pull 완료
- [ ] 문서 확인 완료
- [ ] 원격서버 상태 정상 확인

#### 개발 중
- [ ] 로컬 테스트 통과
- [ ] 커밋 메시지 컨벤션 준수
- [ ] `.env` 파일 커밋 안 함
- [ ] API 키 노출 없음

#### 배포 후
- [ ] GitHub Actions 성공
- [ ] API 헬스체크 정상
- [ ] 로그 에러 없음
- [ ] 로컬-원격 코드 동일

#### 문서화
- [ ] 변경사항 기록
- [ ] 다음 작업자를 위한 메모 작성

---

## 🔗 참고 자료

- **완전 가이드**: [MASTER_GUIDE.md](MASTER_GUIDE.md)
- **프로젝트 개요**: [README.md](README.md)
- **서버 상태**: [SERVER_HEALTH_CHECK_20260104.md](SERVER_HEALTH_CHECK_20260104.md)
- **GitHub 저장소**: https://github.com/joocy75-hash/TradingView-Strategy
- **GitHub Actions**: https://github.com/joocy75-hash/TradingView-Strategy/actions

---

## 📞 문제 발생 시

### 일반적인 문제 해결 순서

1. **로그 확인**: `docker compose logs`
2. **문서 참조**: [MASTER_GUIDE.md](MASTER_GUIDE.md#트러블슈팅)
3. **Git 히스토리**: `git log --oneline -10`
4. **서버 재시작**: `docker compose restart`
5. **롤백**: `git revert <commit>`

### 연락처

- GitHub Issues: https://github.com/joocy75-hash/TradingView-Strategy/issues
- 프로젝트 위키: (설정 예정)

---

**체크리스트 작성**: Claude Sonnet 4.5
**최종 검토**: 2026-01-04 21:22 KST
**다음 업데이트**: 문제 발생 시 또는 프로세스 개선 시
