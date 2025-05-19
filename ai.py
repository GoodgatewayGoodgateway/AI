import json

# 사용자 정보 로드
with open("full_user_data.json", "r", encoding="utf-8") as f:
    users = json.load(f)

# 성향 요약 리포트 함수
def generate_match_report(user):
    mbti = user.get("mbti", "").upper()
    lifestyle = user.get("lifestyle", {})
    interests = user.get("interests", [])
    
    # 규칙 기반 분석
    if "낮음" in lifestyle.get("noise", "") and lifestyle.get("cleanLevel") == "상":
        return "당신은 조용하고 청결한 환경을 중요하게 생각해요. 비슷한 성향의 사람과 잘 맞습니다."
    
    if mbti.startswith("I") and "독서" in interests:
        return "조용한 분위기에서 혼자만의 시간을 즐기는 사람과 잘 어울립니다."
    
    if mbti.startswith("E") and "운동" in interests:
        return "활발하고 함께 활동할 수 있는 룸메이트와 잘 어울려요!"
    
    if "요리" in interests or "카페" in interests:
        return "일상에서 소소한 취미를 공유할 수 있는 사람이 잘 맞습니다."
    
    return "당신의 생활 패턴에 맞는 사람을 분석하고 있어요. 곧 최적의 매칭을 알려드릴게요!"

# 리포트 출력 예시
for user in users:
    if isinstance(user, dict) and "name" in user:
        print(f"👤 {user['name']}님의 매칭 성향 리포트:")
        print("   ", generate_match_report(user))
        print()