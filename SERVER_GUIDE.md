# Multi-Group Server Architecture Guide

이 서버는 여러 독립된 프로젝트(Group A, B, C)를 효율적으로 관리하기 위해 Nginx Reverse Proxy와 Docker Network 격리 구조를 사용합니다.

## 1. 디렉토리 구조

```text
/root/
├── proxy/                # 공통 Nginx 프록시 설정
├── service_a/            # Group A (Freqtrade)
├── service_b/            # Group B (Sports Analysis / Automation)
└── service_c/            # Group C (Strategy Lab)
    └── strategy-research-lab/
```

## 2. 네트워크 구조

- **proxy-net**: Nginx와 각 서비스의 진입점이 공유하는 외부 네트워크입니다.
- **group_x_network**: 각 그룹 내부의 서비스들끼리만 통신하는 격리된 네트워크입니다.

## 3. 포트 할당 가이드라인

| 그룹 | 서비스 | 내부 포트 | 외부 포트 (Proxy) | 직접 접속 포트 |
| :--- | :--- | :--- | :--- | :--- |
| **Proxy** | Nginx | 80, 443 | 80, 443 | - |
| **Group A** | Deep Signal | 8080 | 80 | 8001-8010 |
| **Group B** | Automation | 8080 | 80 | 8021-8030 |
| **Group C** | Strategy Lab | 8080 | 80 | 8081-8090 |

## 4. 관리 스크립트 (`/root/deploy.sh`)

통합 관리 스크립트를 통해 각 그룹을 개별적으로 제어할 수 있습니다.

```bash
# Group C 시작
./deploy.sh group_c up

# Group C 중지
./deploy.sh group_c down

# Group C 로그 확인
./deploy.sh group_c logs

# 프록시 재시작
./deploy.sh proxy restart
```

## 5. 새로운 그룹 추가 방법

1. `/root/group_x` 디렉토리 생성
2. `docker-compose.yml` 작성 시 `proxy-net` 네트워크 추가
3. `/root/proxy/conf.d/group_x.conf` 작성 (Nginx 설정)
4. `deploy.sh`에 경로 추가
5. 프록시 재시작: `./deploy.sh proxy restart`

## 6. SSL/TLS (HTTPS) 설정

현재는 HTTP(80)만 설정되어 있습니다. HTTPS를 적용하려면:

1. `/root/proxy/certs`에 인증서 파일(.crt, .key)을 업로드합니다.
2. `/root/proxy/conf.d/group_c.conf`를 수정하여 443 포트 설정을 추가합니다.
3. `deploy.sh proxy restart`를 실행합니다.

## 7. 트러블슈팅

- **Nginx 시작 실패**: `docker logs global-proxy`로 확인하세요. 업스트림 서비스가 다운되어 있어도 변수(`$upstream_...`)를 사용하므로 Nginx는 정상 시작됩니다.
- **네트워크 연결 오류**: 서비스가 `proxy-net`에 포함되어 있는지 `docker inspect <container>`로 확인하세요.
- **포트 충돌**: `netstat -tulpn` 또는 `docker ps`로 이미 사용 중인 포트를 확인하세요.
