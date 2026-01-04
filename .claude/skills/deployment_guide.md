# Deployment 가이드

> **위치**: `strategy-research-lab/deploy/`
>
> **목적**: 서버 배포 및 운영
>
> **마지막 업데이트**: 2026-01-04

---

## 🌐 서버 정보

| 항목 | 값 |
|------|-----|
| IP | 152.42.169.132 |
| OS | Ubuntu 22.04 LTS |
| 프로젝트 경로 | /opt/strategy-research-lab |

---

## 🚀 배포 명령어

### 서비스 관리

```bash
# 서비스 상태 확인
systemctl status strategy-collector strategy-api nginx

# 수집기 재시작
systemctl restart strategy-collector

# API 서버 재시작
systemctl restart strategy-api

# 로그 확인
journalctl -u strategy-collector -f
tail -f /opt/strategy-research-lab/logs/auto_collect_*.log
```

### API 테스트

```bash
# 헬스체크
curl http://152.42.169.132:8000/api/health

# 통계 조회
curl http://152.42.169.132:8000/api/stats

# 전략 목록
curl http://152.42.169.132:8000/api/strategies?limit=10
```

---

## ⚙️ systemd 서비스 파일

### strategy-collector.service

```ini
[Unit]
Description=TradingView Strategy Collector
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/strategy-research-lab
Environment=PATH=/opt/strategy-research-lab/venv/bin
ExecStart=/opt/strategy-research-lab/venv/bin/python deploy/auto_collector.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### strategy-api.service

```ini
[Unit]
Description=Strategy Research Lab API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/strategy-research-lab
Environment=PATH=/opt/strategy-research-lab/venv/bin
ExecStart=/opt/strategy-research-lab/venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🚨 트러블슈팅

### 서버 접속 타임아웃

```bash
# 방화벽 확인
ufw status

# Nginx 상태 확인
systemctl status nginx

# 포트 리스닝 확인
ss -tlnp | grep -E '80|8000'
```

### 디스크 부족

```bash
# 용량 확인
df -h

# 로그 정리
find /opt/strategy-research-lab/logs -name "*.log" -mtime +30 -delete

# pip 캐시 정리
rm -rf ~/.cache/pip
```

---

## ✅ 작업 시 체크리스트

- [ ] 서비스 파일 수정 시 daemon-reload 실행
- [ ] 환경변수 변경 시 .env 파일 업데이트
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
