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
다음은 부동산 매물에 대한 정보입니다. 이 정보를 바탕으로 사용자에게 설명해줄 문장 한 줄을 생성해주세요
출력은 아래 요약 예시의 말투와 문법을 따라서 작성해주세요

[매물 정보]
- 면적: 약 {current_pyeong}평 ({area}㎡)
- 가격: {total_price}만원 (보증금 {deposit} / 월세 {monthly})
- 유사 매물 평균 면적: 약 {avg_pyeong}평 ({cmp.average_area}㎡)
- 유사 매물 평균 가격: {cmp.average_price}만원
- 현재 매물은 {"더 저렴한 편입니다." if cmp.cheaper_than_average else "비슷하거나 비쌉니다."}
- 주변 편의시설: {cafe_desc}, {store_desc}, {gym_desc}

[출력 예시]
이 매물은 다른 매물과 유사 조건이지만, 평균보다 저렴하고 그리고 ~ 하고 ~ 해서 사용자님에게 더 좋을 것 같아요!

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
