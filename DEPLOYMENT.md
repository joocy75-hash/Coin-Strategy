# 🚀 배포 가이드

> 서버: `141.164.55.245` (Hetzner Cloud)  
> 프로젝트 경로: `/root/service_c/strategy-research-lab`

---

## ⚠️ 핵심 규칙

### ❌ 절대 금지
1. **원격 서버에서 직접 코드 수정 금지**
2. **Docker 컨테이너 내부에서 파일 수정 금지**
3. **로컬과 서버 코드가 다른 상태로 방치 금지**

### ✅ 올바른 배포 순서
```
로컬 수정 → Git 커밋 → GitHub Push → 자동 배포 (5-10분)
```

---

## 📋 배포 절차

### 1. 로컬에서 코드 수정
```bash
# 코드 수정 후 테스트
python -m pytest tests/ -v

# 변경사항 확인
git status
git diff
```

### 2. Git 커밋 및 푸시
```bash
git add .
git commit -m "feat: 변경 내용 설명"
git push origin main
```

### 3. 배포 상태 확인
```bash
# GitHub Actions 상태 확인
gh run list --limit 3

# 배포 로그 확인
gh run view --log | tail -50
```

### 4. 서버 헬스체크
```bash
# 직접 포트 접근 (권장)
curl http://141.164.55.245:8081/api/health

# Nginx 프록시 (설정된 경우)
curl http://141.164.55.245/api/health
```

---

## 🔧 서버 관리 명령어

### SSH 접속
```bash
ssh root@141.164.55.245
```

### Docker 상태 확인
```bash
# 컨테이너 상태
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps

# 로그 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs -f --tail=100

# 재시작
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml restart
```

### 긴급 복구
```bash
# 컨테이너 중지 후 재시작
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml down
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml up -d
```

---

## 🏗️ 환경 격리

### 네트워크 구조
```
proxy-net (외부 접근)
    └── strategy-research-lab (포트 8081)

group_c_network (내부 전용)
    ├── strategy-research-lab
    └── strategy-scheduler
```

### 리소스 제한
| 서비스 | CPU | Memory |
|--------|-----|--------|
| strategy-lab | 2.0 | 2GB |
| scheduler | 1.5 | 1.5GB |

### 다른 프로젝트와 격리
- 전용 네트워크 `group_c_network` 사용
- 컨테이너 이름 prefix로 구분
- 포트 8081 전용 할당

---

## 🔍 트러블슈팅

### 배포 실패 시
```bash
# 1. GitHub Actions 로그 확인
gh run view --log | tail -100

# 2. 서버에서 직접 확인
ssh root@141.164.55.245
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs --tail=100
```

### 서버 응답 없음 (504)
```bash
# 컨테이너 재시작
ssh root@141.164.55.245
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml restart

# 포트 확인
netstat -tlnp | grep 8081
```

### 코드 동기화 문제
```bash
# 로컬 코드 확인
git log -1 --oneline

# 서버 코드 확인
ssh root@141.164.55.245 "cd /root/service_c/strategy-research-lab && git log -1 --oneline 2>/dev/null || head -1 README.md"
```

---

## 📁 주요 파일

| 파일 | 설명 |
|------|------|
| `.github/workflows/deploy.yml` | GitHub Actions 배포 워크플로우 |
| `docker-compose.yml` | Docker 서비스 정의 |
| `Dockerfile` | 컨테이너 이미지 빌드 |
| `.env` | 환경 변수 (서버에만 존재) |

---

## 🔐 보안 체크리스트

- [ ] API 키는 GitHub Secrets에만 저장
- [ ] `.env` 파일은 `.gitignore`에 포함
- [ ] SSH 키는 GitHub Secrets에 저장
- [ ] 서버 방화벽 설정 확인

---

**마지막 업데이트**: 2026-01-13
