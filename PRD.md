# RPD

## 1. 프로젝트 개요

이 프로젝트는 사용자가 입력한 주소와 면적(평), 가격 정보를 바탕으로,

1. 주변 편의시설 조회
2. 유사 매물과의 비교
3. AI 기반 요약 문장 생성
4. 인근 매물 리스트 검색
    
    등의 기능을 FastAPI 기반 웹 서버로 제공하는 시스템입니다.
    

## 2. 주요 기능

### 1) 주변 편의시설 조회

- 입력: 주소 (ex. 서울시 강남구 역삼동)
- 처리: 카카오 API를 통해 카페, 편의점, 헬스장, 공원 등 주변 장소 검색
- 출력: 각 카테고리별 위치 및 이름 데이터 반환

### 2) 유사 매물 비교

- 입력: 면적(평), 보증금, 월세, 위치
- 처리: 네이버 부동산에서 수집한 매물들과 비교하여 평균 가격과 면적 계산
- 출력: 현재 매물이 평균보다 저렴한지 여부, 평균값, 주변 매물 리스트 반환

### 3) AI 요약 문장 생성

- 입력: 매물 정보 + 주변 시설 정보 + 비교 결과
- 처리: OpenAI API를 활용한 AI 문장 생성
- 출력: 사용자가 이해하기 쉬운 1줄 요약 설명

### 4) 지역 기반 매물 리스트 검색

- 입력: 지역 키워드 (ex. 홍대, 서울대입구역, 역삼초등학교 등)
- 처리: 해당 위치 중심으로 복합건물(complex) 매물 + 일반 article 매물 모두 수집
- 출력: 매물 리스트 반환 (위치, 면적, 보증금, 월세, 거리 등 포함)

## 3. 사용 기술 및 라이브러리

| 기술 | 설명 |
| --- | --- |
| Python + FastAPI | 웹 서버 프레임워크 |
| httpx / requests | 외부 API 통신 |
| Kakao API | 주소 → 좌표 변환, 카테고리 장소 검색 |
| OpenAI API | 자연어 요약 문장 생성 |
| Numpy, OpenCV | 시각화 및 거리 계산, 지도 렌더링 |
| Pydantic | 입력/출력 모델 정의 |
| Shapely | 좌표 다각형 포함 여부 확인 |

## 4. 데이터 흐름 요약

1. 사용자가 `/summary` 또는 `/listings/search`에 요청
2. 서버가 주소 → 좌표 변환 (`geolocation.py`)
3. 주변 시설 비동기 수집 (`facilities.py`)
4. 유사 매물 비교 (`comparison.py`)
5. AI 문장 생성 (`summary.py`)
6. 최종 응답 JSON으로 반환

## 5. 주요 폴더 및 파일 구조

```
bash
복사편집
.
├── main.py                  # FastAPI 진입점
├── app/
│   ├── routes/
│   │   └── housing_detail.py
│   ├── schemas.py           # Pydantic 모델들
│   ├── services/
│   │   ├── facilities.py
│   │   ├── geolocation.py
│   │   ├── comparison.py
│   │   └── summary.py
│   └── utils/
│       └── distance.py
├── src/
│   ├── classes.py           # 매물/구역/좌표 관련 클래스 정의
│   └── util.py              # Naver 부동산 API 크롤링 함수들

```

## 6. 사용 시나리오 예시

**예시 1: 요약 요청**

입력: `"address": "서울시 강동구 천호동", "netLeasableArea": 10, "deposit": 60, "monthly": 0`

출력: AI가 생성한 요약 문장 + 주변 시설 + 유사 매물 비교 결과 포함된 JSON

**예시 2: 지역 매물 검색**

입력: `/api/listings/search?query=서울대입구역`

출력: 복합매물 + 일반 article 매물 리스트