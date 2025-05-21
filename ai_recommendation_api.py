from fastapi import FastAPI, HTTPException
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import uvicorn
import re

app = FastAPI()

# Roomit 백엔드 주소
BACKEND_URL = "http://172.28.2.18:8081"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:14b"


# 사용자 벡터 변환
def vectorize_user(user):
    clean_map = {"높음": 2, "중간": 1, "낮음": 0}
    noise_map = {"높음": 2, "보통": 1, "낮음": 0}
    return np.array([
        1 if user["profile"]["smoking"] == "비흡연" else 0,
        1 if user["profile"]["drinking"] != "음주" else 0,
        clean_map.get(user["profile"]["cleanLevel"], 1),
        int(user["profile"]["wakeUpTime"].split(":")[0]),
        int(user["profile"]["sleepTime"].split(":")[0]),
        noise_map.get(user["profile"]["noise"], 1),
        len(user.get("interests", []))
    ])


# 예시 매물 리스트
house_data = [
    {"id": 1, "smoking": False, "drinking": False, "cleanLevel": 2, "wake": 7, "sleep": 23, "noise": 0, "interest_count": 3},
    {"id": 2, "smoking": False, "drinking": True,  "cleanLevel": 1, "wake": 8, "sleep": 24, "noise": 1, "interest_count": 2},
    # {"id": 3, "smoking": True,  "drinking": True,  "cleanLevel": 1, "wake": 10, "sleep": 1, "noise": 2, "interest_count": 1},
]


# 매물 벡터화
def build_house_vectors():
    return [
        np.array([
            1 if not h["smoking"] else 0,
            1 if not h["drinking"] else 0,
            h["cleanLevel"],
            h["wake"],
            h["sleep"],
            h["noise"],
            h["interest_count"]
        ]) for h in house_data
    ]


# Ollama 설명 생성 요청
def generate_reason_with_ollama(user, house):
    prompt = f"""
    사용자 성향:
    - 흡연: {user["profile"]["smoking"]}
    - 음주: {user["profile"]["drinking"]}
    - 청결도: {user["profile"]["cleanLevel"]}
    - 기상 시각: {user["profile"]["wakeUpTime"]}
    - 취침 시각: {user["profile"]["sleepTime"]}
    - 소음 선호도: {user["profile"]["noise"]}
    - 관심사 수: {len(user.get("interests", []))}

    추천된 매물:
    - 흡연: {"비허용" if not house["smoking"] else "허용"}
    - 음주: {"비허용" if not house["drinking"] else "허용"}
    - 청결도: {house["cleanLevel"]}
    - 기상: {house["wake"]}
    - 취침: {house["sleep"]}
    - 소음 수용도: {house["noise"]}
    - 공통 관심사 수: {house["interest_count"]}

    위 정보를 바탕으로 사용자에게 해당 매물이 잘 맞는 이유를
    자연스럽고 정중한 말투로 1문단 이내로 간결하게 한국어로 설명해줘.
    (100자 이내로 부탁해)
    """

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Ollama 설명 생성 실패: {e}"


# Ollama 응답 정리 함수 (불필요한 태그 제거 + 정제 + 길이 제한)
def clean_ollama_response(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").strip()
    return text[:100]  # 100자 이내로 자르기


# 추천 API
@app.get("/recommend/{userId}")
def recommend_for_user(userId: str):
    try:
        response = requests.get(f"{BACKEND_URL}/api/user/{userId}/full")
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
        
        user_data = response.json()
        user_vec = vectorize_user(user_data)
        house_vecs = build_house_vectors()
        similarities = cosine_similarity([user_vec], np.stack(house_vecs))[0]

        recommendations = []
        for house, score in sorted(zip(house_data, similarities), key=lambda x: x[1], reverse=True):
            raw = generate_reason_with_ollama(user_data, house)
            explanation = clean_ollama_response(raw)
            recommendations.append({
                "houseId": house["id"],
                "smoking": "비허용" if not house["smoking"] else "허용",
                "drinking": "비허용" if not house["drinking"] else "허용",
                "cleanLevel": house["cleanLevel"],
                "wake": house["wake"],
                "sleep": house["sleep"],
                "noise": house["noise"],
                "sharedInterestCount": house["interest_count"],
                "aiScore": round(score, 3),
                "aiExplanation": explanation
            })

        return {"userId": userId, "recommendations": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 중 오류 발생: {e}")


# 실행 엔트리포인트
if __name__ == "__main__":
    uvicorn.run("ai_recommendation_api:app", host="0.0.0.0", port=8000, reload=True)
