# ROOMIT AI — 부동산 분석 서비스

> AI 기반 매물 요약·시세 비교·편의시설 분석·추천까지 제공하는 부동산 분석 백엔드

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com/)
[![Swagger](https://img.shields.io/badge/Swagger-Docs-orange)](http://roomitdocs.o-r.kr/)

---

## 개요

ROOMIT는 주소·면적·가격 정보를 입력하면 아래 분석을 자동으로 수행합니다.

- **AI 요약** — Gemini API로 매물 특징을 한 줄로 요약
- **시세 비교** — 주변 유사 매물 대비 가격 적정성 분석
- **편의시설 분석** — 반경 1,500m 내 8개 카테고리 시설 정보
- **매물 검색** — 지역명·역명 기반 인근 매물 수집
- **시세 통계 & 트렌드** — 지역별 평균가·가격 추이
- **매물 점수** — 가격·교통·편의시설을 종합한 0~100점 평가
- **추천 매물** — 예산·면적·유형 조건 기반 가성비 추천
- **즐겨찾기** — 관심 매물 저장 및 관리

---

## API 목록

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/api/summary` | AI 요약 + 시세 비교 + 편의시설 종합 분석 |
| `POST` | `/api/comparison` | 주변 유사 매물과 가격·면적 비교 |
| `GET` | `/api/facilities` | 반경 1,500m 내 편의시설 8개 카테고리 조회 |
| `GET` | `/api/listings/search` | 지역명 기반 매물 검색 (60초 캐시) |
| `GET` | `/api/listings/all` | 전국 13개 주요 도시 매물 일괄 조회 |
| `GET` | `/api/listings/{id}` | ID로 매물 상세 조회 |
| `GET` | `/api/market/stats` | 지역·타입별 시세 통계 (평균가·면적·매물 수) |
| `GET` | `/api/market/trend` | 날짜별 평균 환산가격 추이 |
| `POST` | `/api/score` | 매물 종합 점수 평가 (가격 50% + 편의시설 30% + 교통 20%) |
| `POST` | `/api/recommend` | 예산·면적·유형 조건 기반 추천 매물 |
| `POST` | `/api/favorites` | 즐겨찾기 추가 |
| `GET` | `/api/favorites/{user_id}` | 즐겨찾기 목록 조회 |
| `DELETE` | `/api/favorites/{favorite_id}` | 즐겨찾기 삭제 |

전체 명세는 Swagger에서 확인하세요: **[roomitdocs.o-r.kr](http://roomitdocs.o-r.kr/)**

---

## 폴더 구조

```text
AI/
├── main.py                        # FastAPI 앱 진입점, CORS, lifespan 설정
├── .env                           # API 키 (Kakao, Gemini, DB)
├── requirements.txt
├── app/
│   ├── database.py                # MySQL 초기화, listings / favorites CRUD
│   ├── schemas.py                 # Pydantic 요청·응답 스키마
│   ├── routes/
│   │   └── housing_detail.py      # 전체 API 라우터
│   ├── services/
│   │   ├── geolocation.py         # Kakao 주소 ↔ 좌표 변환
│   │   ├── facilities.py          # Kakao 주변 시설 검색
│   │   ├── comparison.py          # 유사 매물 비교 분석
│   │   ├── summary.py             # Gemini AI 요약 생성
│   │   └── score.py               # 매물 종합 점수 산출
│   └── utils/
│       └── distance.py            # Haversine 거리 계산
└── src/
    ├── classes.py                 # 데이터 모델 (NLocation, NSector 등)
    └── util.py                    # Naver 부동산 API 크롤러
```

---

## 기술 스택

| 분류 | 내용 |
| --- | --- |
| **프레임워크** | Python 3.10+, FastAPI, Uvicorn |
| **데이터베이스** | MySQL (roomitai) |
| **AI** | Google Gemini API (`gemini-2.0-flash` / `1.5-flash`) |
| **지도·위치** | Kakao Maps REST API (주소 변환, 장소 검색) |
| **매물 데이터** | Naver 부동산 비공식 API 크롤링 |
| **비동기** | asyncio, httpx |
| **배포** | GCP Compute Engine (Ubuntu 22.04), systemd, Port 8888 |

---

## 매물 점수 산출 기준

| 항목 | 가중치 | 산출 방식 |
| --- | --- | --- |
| 가격 점수 | 50% | 시세 대비 ±20% 범위에서 선형 변환 |
| 편의시설 점수 | 30% | 반경 1,500m 내 7개 카테고리 합산 (40개 = 100점) |
| 교통 점수 | 20% | 반경 1,500m 내 지하철역 수 (5개 = 100점) |

등급: **S**(90+) / **A**(80+) / **B**(70+) / **C**(60+) / **D**(50+) / **F**

---

## 주요 모듈 의존성

| 파일 | 역할 | 주요 외부 모듈 |
| --- | --- | --- |
| `src/classes.py` | 좌표·매물 데이터 모델 | shapely, numpy, cv2 |
| `src/util.py` | Naver API 크롤러 | requests, haversine, httpx |
| `app/services/geolocation.py` | 주소 ↔ 좌표 변환 | httpx |
| `app/services/facilities.py` | 주변 시설 검색 | httpx |
| `app/services/comparison.py` | 유사 매물 비교 | src.util |
| `app/services/summary.py` | AI 요약 생성 | google-generativeai |
| `app/services/score.py` | 종합 점수 산출 | comparison, facilities |
| `app/database.py` | DB CRUD | mysql-connector-python |

---

## 환경 변수 (.env)

```env
KAKAO_REST_API_KEY=...
GEMINI_API_KEY=...
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=...
HOST=0.0.0.0
PORT=8888
```

---

## 로컬 실행

```bash
pip install -r requirements.txt
python main.py
# Swagger: http://localhost:8888/docs
```

---

## Deployment — Railway

### 1. Railway 프로젝트 생성

1. [railway.app](https://railway.app) 로그인 후 **New Project** 클릭
2. **Deploy from GitHub repo** → 이 레포 선택

### 2. MySQL 플러그인 추가

1. 프로젝트 대시보드 → **+ New** → **Database** → **MySQL** 선택
2. Railway가 `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE` 환경변수를 자동 주입합니다.

### 3. 환경변수 설정

**Settings → Variables** 에서 아래 값을 추가합니다. (`.env.example` 참고)

| 변수 | 설명 |
| --- | --- |
| `KAKAO_REST_API_KEY` | Kakao Developers REST API 키 |
| `GEMINI_API_KEY` | Google AI Studio API 키 |
| `ADMIN_SECRET_KEY` | `/api/admin/reset` 엔드포인트 인증 키 |
| `PORT` | `8888` |

### 4. 배포

Railway가 `Dockerfile`을 감지해 자동 빌드·배포합니다.
헬스체크 경로: `GET /health` → `{"status": "ok"}`

### 5. 확인

```text
https://<your-app>.railway.app/docs   # Swagger UI
https://<your-app>.railway.app/health # 헬스체크
```

---

## 배포 환경 (GCP — 레거시)

- **플랫폼**: GCP Compute Engine (Ubuntu 22.04)
- **실행**: `systemd` 서비스로 백그라운드 상시 실행
- **포트**: 8888 (GCP 방화벽 TCP 허용)
- **Swagger**: [roomitdocs.o-r.kr](http://roomitdocs.o-r.kr/)

---

## 참고 자료

- [NaverRealEstateHarvester](https://github.com/ByungJin-Lee/NaverRealEstateHavester) — 네이버 부동산 크롤링 참고
- [유튜브: 크롤링 방법](https://www.youtube.com/watch?v=xht7-LwT9Ro)
- [코코아빠 블로그](https://cocoabba.tistory.com/56)
