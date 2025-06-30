import logging
import os
import google.generativeai as genai
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")

def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

def interpret_facility_count(name: str, count: int) -> str:
    if count >= 15:
        return f"{name}이(가) 많은 편입니다"
    elif count <= 5:
        return f"{name}이(가) 적은 편입니다"
    else:
        return f"{name}이(가) 보통 수준입니다"

def build_prompt(area: float, deposit: int, monthly: int, fac: FacilitySummary, cmp: ComparisonResult) -> str:
    total_price = deposit + (monthly * 10)

    # 예시 편의시설 해석
    cafe_desc = interpret_facility_count("카페", len(fac.cafes))
    store_desc = interpret_facility_count("편의점", len(fac.convenience_stores))
    gym_desc = interpret_facility_count("헬스장", len(fac.gyms))

    current_pyeong = to_pyeong(area)
    avg_pyeong = to_pyeong(cmp.average_area)

    return f"""
당신은 부동산 요약 AI입니다.
아래의 매물 데이터를 기반으로, **한 줄 요약 문장**을 생성해주세요. 출력은 따뜻하고 설득력 있는 말투로, 마치 상담사가 사용자에게 말하듯 작성해주세요.

[매물 정보]
- 면적: 약 {current_pyeong}평 ({area}㎡)
- 가격: {total_price}만원 (보증금 {deposit} / 월세 {monthly})
- 유사 매물 평균 면적: 약 {avg_pyeong}평 ({cmp.average_area}㎡)
- 유사 매물 평균 가격: {cmp.average_price}만원
- 현재 매물은 {"더 저렴한 편입니다." if cmp.cheaper_than_average else "비슷하거나 비쌉니다."}
- 주변 편의시설: {cafe_desc}, {store_desc}, {gym_desc}

[출력 예시]
1. 이 매물은 비슷한 다른 매물보다 가격이 저렴하고, 주변에 카페와 편의점이 많아 생활 편의성이 뛰어납니다!
2. 넓은 면적 대비 저렴한 가격에, 주변에 헬스장과 상점이 가까워 생활하기 좋습니다.
3. 주변 환경도 좋고 평균보다 저렴한 조건이라 추천드릴 수 있어요!

[당신의 출력]
""".strip()

def generate_summary(req: HousingRequest, fac: FacilitySummary, cmp: ComparisonResult) -> str:
    try:
        area_m2 = pyeong_to_m2(req.netLeasableArea)
        prompt = build_prompt(area_m2, req.deposit, req.monthly, fac, cmp)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.warning(f"[Gemini 요약 실패] {e}")
        return "요약을 생성할 수 없습니다. 나중에 다시 시도해주세요."
