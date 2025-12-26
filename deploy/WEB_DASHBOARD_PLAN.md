# 웹 대시보드 배포 작업 계획서

## 개요

현재 로컬 HTML 파일로만 볼 수 있는 리포트 시스템을 서버에서 웹으로 접근 가능하도록 배포하는 작업입니다.

---

## 현재 상태

### 기존 구현물
| 파일 | 설명 | 위치 |
|------|------|------|
| `beginner_report.html` | 초보자용 리포트 | `data/beginner_report.html` |
| `report.html` | 일반 리포트 | `data/report.html` |
| `generate_beginner_report.py` | 초보자 리포트 생성 스크립트 | `scripts/` |
| `generate_report.py` | 일반 리포트 생성 스크립트 | `scripts/` |

### 기존 기능
- 카드뷰 / 테이블뷰 토글
- 필터링 (검색, 등급, 권장여부, 최소점수)
- 정렬 (점수, 좋아요, 등급 등)
- 상세 모달 (Pine Script 코드, 분석 결과)
- 툴팁 (리페인팅, 오버피팅, 백테스트 용어 설명)
- 다크테마 UI

### 서버 정보
- **IP**: 152.42.169.132
- **OS**: Ubuntu 22.04 LTS
- **프로젝트 경로**: `/opt/strategy-research-lab`
- **SSH 접속**: `ssh root@152.42.169.132` (비밀번호: `Wnrkswl!23`)

---

## 구현 옵션

### Option A: 정적 파일 서빙 (간단, 권장)

Nginx로 정적 HTML 파일을 서빙하는 방식

**장점**:
- 구현 간단 (30분 내 완료)
- 서버 리소스 최소 사용
- 기존 HTML 파일 그대로 사용

**단점**:
- 실시간 데이터 반영 불가 (리포트 재생성 필요)
- API 없음

### Option B: FastAPI + 정적 파일 (중간)

FastAPI로 API 제공 + 기존 HTML 서빙

**장점**:
- REST API로 실시간 데이터 조회 가능
- 기존 HTML 파일 활용
- 확장성 있음

**단점**:
- 추가 개발 필요 (2-3시간)
- 서버 리소스 추가 사용

### Option C: FastAPI + React SPA (풀스택)

완전한 웹 애플리케이션

**장점**:
- 실시간 데이터, 인터랙티브 UI
- 확장성 최고

**단점**:
- 개발 시간 많이 필요
- 프론트엔드 빌드 환경 필요

---

## 권장 구현: Option A + B 하이브리드

정적 파일 서빙 + 간단한 API 추가

---

## 상세 구현 계획

### Phase 1: Nginx 설치 및 정적 파일 서빙

#### 1.1 Nginx 설치
```bash
ssh root@152.42.169.132

apt update
apt install -y nginx
systemctl enable nginx
systemctl start nginx
```

#### 1.2 Nginx 설정 파일 생성
```bash
nano /etc/nginx/sites-available/strategy-lab
```

```nginx
server {
    listen 80;
    server_name 152.42.169.132;

    # 정적 리포트 파일
    location / {
        root /opt/strategy-research-lab/data;
        index beginner_report.html;
        try_files $uri $uri/ /beginner_report.html;
    }

    # 리포트 파일 직접 접근
    location /report {
        alias /opt/strategy-research-lab/data;
        index beginner_report.html;
    }

    # API 프록시 (Phase 2에서 사용)
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 1.3 설정 활성화
```bash
ln -s /etc/nginx/sites-available/strategy-lab /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

#### 1.4 방화벽 설정
```bash
ufw allow 80/tcp
ufw allow 443/tcp
```

#### 1.5 리포트 자동 생성 추가
`auto_collector.py`에 리포트 생성 로직 추가:

```python
# auto_collector.py의 run_collection_cycle() 끝에 추가
from scripts.generate_beginner_report import generate_beginner_report

# 수집 사이클 완료 후 리포트 생성
await generate_beginner_report(
    db_path=str(PROJECT_ROOT / "data" / "strategies.db"),
    output_path=str(PROJECT_ROOT / "data" / "beginner_report.html")
)
logger.info("HTML 리포트 생성 완료")
```

---

### Phase 2: FastAPI REST API 추가

#### 2.1 API 서버 파일 생성

**파일**: `/opt/strategy-research-lab/api/server.py`

```python
#!/usr/bin/env python3
"""
Strategy Research Lab REST API
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI(title="Strategy Research Lab API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path("/opt/strategy-research-lab/data/strategies.db")
DATA_DIR = Path("/opt/strategy-research-lab/data")


class StrategyItem(BaseModel):
    script_id: str
    title: str
    author: str
    likes: int
    total_score: float
    grade: str
    repainting_score: float
    overfitting_score: float


class StatsResponse(BaseModel):
    total_strategies: int
    analyzed_count: int
    passed_count: int
    avg_score: float


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """통계 정보 조회"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM strategies")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM strategies WHERE total_score IS NOT NULL")
    analyzed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM strategies WHERE grade IN ('A', 'B')")
    passed = cur.fetchone()[0]

    cur.execute("SELECT AVG(total_score) FROM strategies WHERE total_score IS NOT NULL")
    avg = cur.fetchone()[0] or 0

    conn.close()

    return StatsResponse(
        total_strategies=total,
        analyzed_count=analyzed,
        passed_count=passed,
        avg_score=round(avg, 1)
    )


@app.get("/api/strategies", response_model=List[StrategyItem])
async def get_strategies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0, ge=0, le=100),
    grade: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("total_score"),
    sort_order: str = Query("desc")
):
    """전략 목록 조회"""
    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT script_id, title, author, likes, total_score, grade,
               repainting_score, overfitting_score
        FROM strategies
        WHERE total_score IS NOT NULL
          AND total_score >= ?
    """
    params = [min_score]

    if grade:
        query += " AND grade = ?"
        params.append(grade)

    if search:
        query += " AND (title LIKE ? OR author LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    # 정렬
    valid_sort_columns = ["total_score", "likes", "title", "grade"]
    if sort_by in valid_sort_columns:
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {order}"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        StrategyItem(
            script_id=row["script_id"],
            title=row["title"],
            author=row["author"],
            likes=row["likes"] or 0,
            total_score=row["total_score"] or 0,
            grade=row["grade"] or "F",
            repainting_score=row["repainting_score"] or 0,
            overfitting_score=row["overfitting_score"] or 0
        )
        for row in rows
    ]


@app.get("/api/strategy/{script_id}")
async def get_strategy_detail(script_id: str):
    """전략 상세 정보 조회"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM strategies WHERE script_id = ?
    """, [script_id])

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"error": "Strategy not found"}

    return dict(row)


# 정적 파일 서빙
@app.get("/")
async def serve_index():
    return FileResponse(DATA_DIR / "beginner_report.html")


# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2.2 API 서비스 파일

**파일**: `/etc/systemd/system/strategy-api.service`

```ini
[Unit]
Description=Strategy Research Lab API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/strategy-research-lab
Environment=PATH=/opt/strategy-research-lab/venv/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/strategy-research-lab/venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2.3 서비스 시작
```bash
# 의존성 설치
source /opt/strategy-research-lab/venv/bin/activate
pip install fastapi uvicorn

# 서비스 등록 및 시작
systemctl daemon-reload
systemctl enable strategy-api
systemctl start strategy-api
```

---

### Phase 3: HTTPS 설정 (선택)

Let's Encrypt로 무료 SSL 인증서 적용

```bash
apt install -y certbot python3-certbot-nginx

# 도메인이 있는 경우
certbot --nginx -d your-domain.com

# 또는 자체 서명 인증서
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt
```

---

## 파일 구조 (구현 후)

```
/opt/strategy-research-lab/
├── api/
│   ├── __init__.py
│   └── server.py              # FastAPI 서버
├── data/
│   ├── strategies.db          # SQLite DB
│   ├── beginner_report.html   # 초보자 리포트
│   └── report.html            # 일반 리포트
├── deploy/
│   ├── auto_collector.py      # 자동 수집 (리포트 생성 포함)
│   ├── strategy-collector.service
│   └── strategy-api.service   # API 서비스
├── scripts/
│   ├── generate_beginner_report.py
│   └── generate_report.py
└── venv/
```

---

## 접속 URL (구현 후)

| URL | 설명 |
|-----|------|
| `http://152.42.169.132/` | 메인 대시보드 (초보자 리포트) |
| `http://152.42.169.132/report.html` | 일반 리포트 |
| `http://152.42.169.132/api/stats` | 통계 API |
| `http://152.42.169.132/api/strategies` | 전략 목록 API |
| `http://152.42.169.132/api/strategy/{id}` | 전략 상세 API |
| `http://152.42.169.132/api/docs` | API 문서 (Swagger) |

---

## 구현 체크리스트

### Phase 1: 정적 파일 서빙
- [ ] Nginx 설치
- [ ] Nginx 설정 파일 생성
- [ ] 설정 활성화 및 테스트
- [ ] 방화벽 포트 열기
- [ ] `auto_collector.py`에 리포트 생성 로직 추가
- [ ] 서비스 재시작 및 테스트

### Phase 2: REST API
- [ ] `api/` 디렉토리 생성
- [ ] `server.py` 작성
- [ ] FastAPI, uvicorn 설치
- [ ] systemd 서비스 파일 생성
- [ ] 서비스 시작 및 테스트
- [ ] API 문서 확인

### Phase 3: HTTPS (선택)
- [ ] 도메인 연결 또는 자체 서명 인증서
- [ ] Nginx SSL 설정
- [ ] HTTP → HTTPS 리다이렉트

---

## 예상 소요 시간

| Phase | 작업 | 시간 |
|-------|------|------|
| 1 | Nginx 정적 파일 서빙 | 30분 |
| 2 | FastAPI REST API | 2시간 |
| 3 | HTTPS 설정 | 30분 |
| **합계** | | **3시간** |

---

## 주의사항

1. **서버 재시작 후에도 서비스 자동 시작**: `systemctl enable` 필수
2. **리포트 자동 갱신**: 수집 사이클마다 HTML 리포트 재생성
3. **API 보안**: 필요시 API 키 또는 IP 화이트리스트 추가
4. **백업**: DB 파일 정기 백업 권장

---

## 참고 명령어

```bash
# 서비스 상태 확인
systemctl status nginx
systemctl status strategy-api
systemctl status strategy-collector

# 로그 확인
journalctl -u nginx -f
journalctl -u strategy-api -f

# Nginx 설정 테스트
nginx -t

# 포트 확인
ss -tlnp | grep -E '80|8000'
```

---

## 작성자

- **작성일**: 2025-12-25
- **작성자**: Claude Code
- **버전**: 1.0
