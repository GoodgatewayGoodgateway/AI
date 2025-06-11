from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# ✅ 올바른 모델 ID로 로드
model_id = "allganize/Llama-3-Alpha-Ko-8B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float32,
    device_map={"": "cpu"}
)
model.eval()

app = FastAPI()

# --- 입력 데이터 스키마 ---
class Profile(BaseModel):
    name: str
    age: int
    gender: str
    location: str
    job: str
    introduction: str
    idealRoommate: str
    mbti: str
    wakeUpTime: str
    sleepTime: str
    dayNightType: str
    cleanLevel: str
    noise: str
    smoking: str
    drinking: str
    avatar: str

class UserData(BaseModel):
    userId: str
    email: str
    profile: Profile
    interests: list[str]
    selectedOptions: list[str]

class SummaryResponse(BaseModel):
    summary: str

# --- 프롬프트 생성 ---
def build_prompt(user: UserData) -> str:
    p = user.profile
    interests = list(dict.fromkeys(user.interests))[:5]
    interests_str = ", ".join(interests)

    prompt = f"""
아래는 당신의 라이프스타일과 성향 정보입니다.
이 정보를 바탕으로, 당신의 성격을 "당신은 ~" 으로 시작하여 한 문장으로 요약해 주세요.
또한 어떤 사람과 잘 어울릴지도 함께 알려주세요.

나이: {p.age}
성별: {p.gender}
직업: {p.job}
MBTI: {p.mbti}
기상 시간: {p.wakeUpTime}, 취침 시간: {p.sleepTime}
활동 유형: {p.dayNightType}
청결 수준: {p.cleanLevel}
소음 민감도: {p.noise}
흡연 여부: {p.smoking}, 음주 여부: {p.drinking}
관심사: {interests_str}

요약:"""
    return prompt.strip()

# --- 생성 함수 ---
def generate_summary(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=120,  # ← 충분히 긴 출력 허용
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id
        )
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return text.split("요약:")[-1].strip()

# --- API 엔드포인트 ---
@app.post("/generate-summary", response_model=SummaryResponse)
def create_summary(user: UserData):
    prompt = build_prompt(user)
    summary = generate_summary(prompt)
    return SummaryResponse(summary=summary)
