# ROOMIT AI 부동산 분석 시스템

ROOMIT는 사용자에게 더 나은 주거 결정을 돕기 위해 **AI 기반 부동산 분석 기능**을 제공합니다.

주소, 면적, 가격 정보를 입력하면 아래 기능을 통해 직관적인 분석 결과를 제공합니다.

## 핵심 기능

### AI 요약 문장 생성

- OpenAI API를 사용하여 매물 정보와 주변 환경을 바탕으로
- **자연스러운 한 줄 요약 문장 생성**
- 사용자에게 매물의 특징을 직관적으로 설명

### 유사 매물 비교 분석

- 같은 지역의 유사 매물을 크롤링해
- **평균 가격 및 면적 대비 현재 매물이 저렴한지 분석**
- 정량적 지표로 가격 적정성 판단

### 주변 편의시설 자동 분석

- Kakao API로 **카페, 편의점, 헬스장, 공원, 병원, 은행 등** 위치 데이터 수집
- AI가 해석 가능한 형태로 **시설 밀집도 데이터 제공**

### 지역 기반 매물 수집

- 주소, 동네, 지하철역, 학교 등을 기반으로 인근 매물 자동 검색
- **복합건물(complex) 및 일반 article 매물**을 모두 포함해 통합 제공

---

## API 요약

| 기능 | 경로 | 설명 |
| --- | --- | --- |
| AI 요약 문장 | `/api/summary` | OpenAI 기반 매물 요약 문장 생성 |
| 주변 편의시설 | `/api/facilities` | Kakao 장소 API 기반 주변 시설 목록 반환 |
| 매물 비교 분석 | `/api/summary` 내부 포함 | 주변 유사 매물과 비교하여 가격/면적 차이 분석 |
| 지역 매물 검색 | `/api/listings/search` | 키워드 기반 인근 매물 목록 검색 |
| 매물 상세 조회 | `/api/listings/{id}` | 선택한 매물의 상세 정보 반환 |

---

## 배포 환경

- **플랫폼**: Google Cloud Platform (GCP) – Compute Engine (Ubuntu 22.04)
- **서버 실행 방식**: `systemd`로 백그라운드 실행 유지
- **API 포트**: 8888 (Uvicorn 실행)
- **보안 설정**:
    - GCP 방화벽에서 TCP 8888 포트 허용
    - `.env`를 통해 외부 API 키 및 환경변수 관리
- **Swagger 문서**:
    
    http://roomitdocs.o-r.kr/
    

---

## 폴더 구조

```
.
├── main.py
├── app/
│   ├── routes/
│   │   └── housing_detail.py
│   ├── schemas.py
│   ├── services/
│   │   ├── comparison.py
│   │   ├── facilities.py
│   │   ├── geolocation.py
│   │   └── summary.py
│   └── utils/
│       └── distance.py
├── src/
│   ├── classes.py
│   └── util.py

```

---

## 기술 스택

- **Python**, **FastAPI**
- **OpenAI API** (AI 요약 생성)
- **Kakao Maps API** (주소 ↔ 좌표 변환, 장소 검색)
- **Naver 부동산 비공식 API 크롤링**
- OpenCV, Shapely, numpy (지도 시각화 및 좌표 계산)

---

## Naver 부동산 크롤링 관련 모듈

| 모듈명 | 역할 |
| --- | --- |
| **requests** | 네이버 부동산 HTTP 요청 처리 (`GET` 등) |
| **haversine** | 두 좌표 간 거리 계산 |
| **httpx** | Kakao API 비동기 요청 |
| **dotenv** | `.env`에서 API 키 로드 |
| **shapely** | 지도 상 Sector 내 포함 여부 확인 |
| **numpy (np)** | 좌표 및 도형 연산, 시각화 보조 |
| **cv2 (OpenCV)** | 지도 렌더링 (사용하지 않았을 수도 있음) |
| **src.classes** | 부동산 데이터 모델 (NLocation, NSector 등) |
| **src.util** | Naver 부동산 API 호출 함수 (get_sector 등) |
| **app.services.geolocation** | Kakao 주소 ↔ 좌표 변환 |
| **app.services.facilities** | Kakao 주변시설 검색 |
| **app.services.comparison** | 매물 비교 분석 |
| **app.services.summary** | OpenAI API 요약 호출 |

---

## 커스텀 모듈별 외부 모듈 사용 현황

| 폴더 | 파일 | 역할 | 외부 모듈 |
| --- | --- | --- | --- |
| src | classes.py | 좌표 및 매물 데이터 정의 | shapely, numpy, cv2 |
| src | util.py | Naver API 크롤러 | requests, haversine |
| app/services | geolocation.py | Kakao 주소 ↔ 좌표 변환 | httpx, dotenv |
| app/services | facilities.py | Kakao 주변 시설 검색 | httpx, dotenv |
| app/services | comparison.py | 매물 비교 분석 | src.util |
| app/services | summary.py | OpenAI 요약 호출 | openai, dotenv |

---

## 참고 자료

- [NaverRealEstateHarvester](https://github.com/ByungJin-Lee/NaverRealEstateHavester): 네이버 부동산 데이터 크롤링 참고
- [유튜브: 크롤링 방법](https://www.youtube.com/watch?v=xht7-LwT9Ro): 크롤링 방법 아이디어
- [코코아빠 블로그](https://cocoabba.tistory.com/56): 개발 시 참고한 기술 블로그

---
