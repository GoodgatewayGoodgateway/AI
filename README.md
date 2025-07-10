# ROOMIT AI 부동산 분석 시스템

이 프로젝트는 ROOMIT 사용자에게 더 나은 주거 결정을 돕기 위한 **AI 기반의 부동산 분석 도구**입니다.  
입력한 주소와 면적, 가격 정보를 바탕으로 다음과 같은 기능을 제공합니다.

## 핵심 특징

### AI 요약 문장 생성

- 사용자가 입력한 매물 정보(면적, 가격, 위치)와 주변 편의시설, 비교 결과를 종합하여
- **Gemini API를 통해 자연스럽고 간단한 한 줄 요약 문장을 생성**합니다.
- ROOMIT 사용자에게 직관적인 설명을 제공하여 빠른 판단을 도와줍니다.

### 유사 매물 비교 분석

- 같은 지역 내 비슷한 면적의 전세/월세 매물 데이터를 크롤링하여
- 평균 가격 및 면적과의 차이를 정량적으로 분석합니다.
- 현재 매물이 평균보다 **더 저렴한지 여부도 함께 판단**합니다.

### 주변 편의시설 자동 분석

- 카카오 API를 활용하여 주변의 카페, 편의점, 헬스장, 공원, 병원, 은행 등을 수집
- 각 카테고리별 개수를 바탕으로 **시설 밀집도를 AI에게 해석할 수 있도록 제공**합니다.

### 지역 기반 매물 수집

- 주소, 동네, 역세권, 학교 등 키워드를 통해 해당 위치 중심의 매물 리스트를 자동 수집
- 복합건물(complex) 기반과 일반 article 기반의 매물을 **모두 병합해 보여줍니다**

---

## API 요약

| 기능 | 경로 | 설명 |
|------|------|------|
| AI 요약 문장 | `/api/summary` | 사용자가 입력한 매물 정보에 대해 Gemini 기반 요약 문장 생성 |
| 주변 편의시설 | `/api/facilities` | 카카오 장소 API를 통해 위치 기반 편의시설 목록 반환 |
| 매물 비교 분석 | `/api/summary` 내부 포함 | 주변 유사 매물과 비교하여 평균 가격/면적 대비 여부 판단 |
| 지역 매물 검색 | `/api/listings/search` | 주소/지하철/학교 등 키워드 기반 인근 매물 수집 |
| 매물 상세 조회 | `/api/listings/{id}` | 리스트에서 선택한 매물의 상세 정보 확인 |

---

## 배포 환경

- **플랫폼**: Google Cloud Platform (GCP) – Compute Engine (Ubuntu 22.04)
- **서버 실행 방식**: `systemd` 서비스 등록으로 콘솔 종료 시에도 지속 실행
- **API 실행 포트**: `8888`번 포트에서 FastAPI(Uvicorn) 구동
- **보안 설정**:
    - GCP 방화벽에서 `tcp:8888` 포트 허용함
    - `.env`를 통해 외부 API 키 및 실행 정보 관리
- **Swagger UI**:
    
    `http://roomitdocs.o-r.kr/` (FastAPI Swagger UI)

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

- Python, FastAPI
- Gemini API (AI 요약 생성)
- Kakao Maps API (주소 ↔ 좌표 변환, 장소 정보 검색)
- Naver 부동산 비공식 API 크롤링
- OpenCV, Shapely, numpy (지도 시각화, 좌표 연산 등)

---

## Naver 부동산 비공식 API 크롤링을 위해 쓰인 모듈
| 모듈명              | 용도                                      |
| ---------------- | --------------------------------------- |
| **requests**     | 네이버 부동산 API에 HTTP 요청 (`GET`, 헤더 설정 등)   |
| **haversine**    | 두 좌표 간 거리 계산 (단위: m/km)                 |
| **httpx**        | Kakao API 비동기 요청용 (편의시설, 좌표 변환 등)       |
| **dotenv**       | `.env`에서 Kakao API Key 로드               |
| **shapely**      | Sector 내 포함 여부 확인용 (좌표 → 다각형)           |
| **numpy (np)**   | 좌표/도형 처리, 이미지 렌더링 보조                    |
| **cv2 (OpenCV)** | Sector 지도 렌더링 시 사용 (단 실제 사용 안 했을 수도 있음) |
| **src.classes**              | NLocation, NSector, NThing 등 부동산 관련 데이터 클래스                 |
| **src.util**                 | get\_sector, get\_things, distance\_between 등 네이버 API 호출 함수 |
| **app.services.geolocation** | Kakao 주소 ↔ 좌표 변환                                            |
| **app.services.facilities**  | Kakao 주변시설 검색                                               |
| **app.services.comparison**  | 매물 비교                                                       |
| **app.services.summary**     | Gemini API 요약 호출                                            |

## 커스텀 모듈에 쓰인 외부 모듈
| 폴더           | 파일             | 역할               | 외부 모듈               |
| ------------ | -------------- | ---------------- | ------------------- |
| src          | classes.py     | 좌표/매물 데이터 클래스    | shapely, numpy, cv2 |
| src          | util.py        | Naver API 크롤러    | requests, haversine |
| app/services | geolocation.py | Kakao 주소 ↔ 좌표 변환 | httpx, dotenv       |
| app/services | facilities.py  | Kakao 편의시설 검색    | httpx, dotenv       |
| app/services | comparison.py  | 매물 비교            | src.util            |
| app/services | summary.py     | Gemini API 요약    | httpx, dotenv       |


---

## 참고 자료

- https://github.com/ByungJin-Lee/NaverRealEstateHavester (네이버 아파트 부동산 가격 AI에서 크롤링 하는 부분을 가져옴)
- https://www.youtube.com/watch?v=xht7-LwT9Ro (다양한 크롤링 방법을 시도하게 함)
- https://cocoabba.tistory.com/56 (이 티스토리에서 참고 많이 함)
