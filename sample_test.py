import json
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline
import torch

# 모델 이름
model_path = "KoAlpaca-Polyglot-5.8B"

# 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 모델 로드
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    device_map="auto",
)

# 텍스트 생성 파이프라인
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

# 사용자 데이터 불러오기
with open("user_data.json", "r", encoding="utf-8") as f:
    users = json.load(f)

def make_prompt(user):
    prompt = f"""
다음은 사용자의 정보입니다. 이 사용자의 데이터를 기반으로 줄글 설명으로 요약해 주세요.

사용자 정보:
이름: {user['name']}
나이: {user['age']}
직업: {user['job']}
거주지: {user['location']}
MBTI: {user['mbti']}
소개: {user['introduction']}
관심사: {", ".join(user['interests'])}
흡연 여부: {user['smoking']}
음주 여부: {user['drinking']}
이상적인 룸메이트: {user['idealRoommate']}

생활 습관:
"""
    for section in user["lifestyle"]:
        prompt += f"- {section['title']}\n"
        for item in section["items"]:
            prompt += f"  • {item['label']}: {item['value']}\n"
    prompt += "\n줄글 요약:"
    return prompt.strip()

# 줄글 생성
for user in users:
    prompt = make_prompt(user)
    result = generator(prompt, max_new_tokens=300, do_sample=True, temperature=0.7)[0]["generated_text"]
    
    # 요약 부분만 추출
    summary = result.split("줄글 요약:")[-1].strip()
    print(f"\n📝 {user['name']} 님에 대한 요약:\n{summary}\n")
