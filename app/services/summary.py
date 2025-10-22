import logging
import os
import google.generativeai as genai
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from dotenv import load_dotenv
import time
import random

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 여러 Gemini 모델을 로테이션하여 사용 (Rate Limit 방지)
AVAILABLE_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

SUMMARY_CACHE = {}
MODEL_FAILURE_COUNT = {model_name: 0 for model_name in AVAILABLE_MODELS}

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
다음은 부동산 매물에 대한 정보입니다. 이 정보를 바탕으로 사용자에게 설명해줄 문장 한 줄을 생성해주세요.
출력은 아래 요약 예시의 말투와 문법을 따라서 작성해주세요.

[매물 정보]
- 면적: 약 {current_pyeong}평 ({area}㎡)
- 가격: {total_price}만원 (보증금 {deposit} / 월세 {monthly})
- 유사 매물 평균 면적: 약 {avg_pyeong}평 ({cmp.average_area}㎡)
- 유사 매물 평균 가격: {cmp.average_price}만원
- 현재 매물은 {"더 저렴한 편입니다." if cmp.cheaper_than_average else "비슷하거나 비쌉니다."}
- 주변 편의시설: {cafe_desc}, {store_desc}, {gym_desc}

[출력 예시]
이 매물은 다른 매물과 유사 조건이지만, 평균보다 저렴하고 ~ 해서 사용자님에게 더 좋을 것 같아요!

[당신의 출력]
""".strip()

def get_best_available_model() -> str:
    """실패 횟수가 가장 적은 모델을 선택"""
    sorted_models = sorted(AVAILABLE_MODELS, key=lambda m: MODEL_FAILURE_COUNT[m])
    # 실패 횟수가 같으면 랜덤으로 선택
    best_count = MODEL_FAILURE_COUNT[sorted_models[0]]
    best_models = [m for m in sorted_models if MODEL_FAILURE_COUNT[m] == best_count]
    return random.choice(best_models)

def generate_summary(req: HousingRequest, fac: FacilitySummary, cmp: ComparisonResult) -> str:
    try:
        # 입력값 캐싱 키 생성
        cache_key = (req.address, req.deposit, req.monthly, req.netLeasableArea)
        if cache_key in SUMMARY_CACHE:
            return SUMMARY_CACHE[cache_key]

        area_m2 = pyeong_to_m2(req.netLeasableArea)
        prompt = build_prompt(area_m2, req.deposit, req.monthly, fac, cmp)

        # 모든 모델을 시도 (Rate Limit 회피)
        tried_models = []
        for attempt in range(len(AVAILABLE_MODELS)):
            try:
                # 가장 성공률이 높은 모델 선택
                model_name = get_best_available_model()
                
                # 이미 시도한 모델은 제외
                if model_name in tried_models:
                    # 모든 모델을 시도했으면 다음으로
                    remaining = [m for m in AVAILABLE_MODELS if m not in tried_models]
                    if not remaining:
                        break
                    model_name = random.choice(remaining)
                
                tried_models.append(model_name)
                model = genai.GenerativeModel(model_name)
                
                start = time.time()
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": 5}
                )
                duration = round(time.time() - start, 2)
                
                text = response.text.strip()
                
                # 성공하면 실패 카운트 감소 (최소 0)
                MODEL_FAILURE_COUNT[model_name] = max(0, MODEL_FAILURE_COUNT[model_name] - 1)
                
                logging.info(f"[Gemini 요약 완료] 모델: {model_name}, {duration}초 소요")
                
                # 캐시에 저장
                SUMMARY_CACHE[cache_key] = text
                return text
                
            except Exception as e:
                error_msg = str(e)
                
                # Rate Limit 에러면 해당 모델의 실패 카운트 증가
                if "429" in error_msg or "Resource has been exhausted" in error_msg:
                    MODEL_FAILURE_COUNT[model_name] = MODEL_FAILURE_COUNT.get(model_name, 0) + 5
                    logging.warning(f"[Rate Limit] {model_name} - 다른 모델로 시도합니다.")
                else:
                    MODEL_FAILURE_COUNT[model_name] = MODEL_FAILURE_COUNT.get(model_name, 0) + 1
                    logging.warning(f"[{model_name} 실패] {e}")
                
                time.sleep(0.3)

        return "요약을 생성할 수 없습니다. 나중에 다시 시도해주세요."

    except Exception as e:
        logging.warning(f"[Gemini 요약 실패] {e}")
        return "요약을 생성할 수 없습니다. 나중에 다시 시도해주세요."
