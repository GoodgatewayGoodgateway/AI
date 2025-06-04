from fastapi import FastAPI, HTTPException
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import uvicorn
import re
import google.generativeai as genai
import os

app = FastAPI()

# Roomit 백엔드 주소
BACKEND_URL = "http://172.28.2.18:8082"

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyA1ZkSTHki91LwNyB5623ik9bbSVGU6ODE"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

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

# Gemini 설명 생성 요청
def generate_reason_with_gemini(user, house):
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

    이 정보를 바탕으로 사용자에게 해당 매물이 잘 맞는 이유를
    자연스럽고 정중한 말투로 간결하게 한 문단으로 한국어로 설명해줘.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gemini 설명 생성 실패: {e}"

# 설명 정제 함수
def clean_gemini_response(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").strip()
    sentences = re.split(r'(?<=[.다요])\s+', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if 10 <= len(sentence) <= 100:
            return sentence
    return "사용자의 성향에 잘 맞는 매물입니다."

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
            raw = generate_reason_with_gemini(user_data, house)
            explanation = clean_gemini_response(raw)
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


# 실행
if __name__ == "__main__":
    uvicorn.run("ai_recommendation_api:app", host="0.0.0.0", port=8000, reload=True)
