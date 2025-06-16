import os
import google.generativeai as genai
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("models/gemini-1.5-flash")

def build_prompt(req: HousingRequest, fac: FacilitySummary, cmp: ComparisonResult) -> str:
    return f"""
다음은 부동산 매물에 대한 정보입니다. 이 정보를 바탕으로 사람들에게 설명해줄 간결한 문장 요약 예시의 말투와 문법에 따라 문장을 생성해주세요.

- 면적: {req.area}㎡
- 가격: {req.price}만원
- 주변 편의시설: 카페 {len(fac.cafes)}곳, 편의점 {len(fac.convenience_stores)}곳, 헬스장 {len(fac.gyms)}곳
- 유사 매물 평균 면적: {cmp.average_area}㎡
- 유사 매물 평균 가격: {cmp.average_price}만원
- 현재 매물은 {"더 저렴한 편입니다." if cmp.cheaper_than_average else "비슷하거나 비쌉니다."}

요약 예시:  
"이 매물은 다른 매물과 유사 조건이지만 ~~ 하고 ~~ 해서 더 좋을것 같아요!"

당신의 출력:
""".strip()

def generate_summary(req: HousingRequest, fac: FacilitySummary, cmp: ComparisonResult) -> str:
    prompt = build_prompt(req, fac, cmp)
    response = model.generate_content(prompt)
    return response.text.strip()
