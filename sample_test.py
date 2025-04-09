import json
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline
import torch

model_path = "KoAlpaca-Polyglot-5.8B"

tokenizer = AutoTokenizer.from_pretrained(model_path)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    device_map="auto",
)

generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

with open("user_data.json", "r", encoding="utf-8") as f:
    users = json.load(f)

def make_prompt(user):
    prompt = f"""
당신은 아래 사용자 정보를 바탕으로, 줄글이 아닌 **숫자가 매겨진 5개의 문장**으로 구성된 설명문을 작성하는 AI입니다.  
사용자에 대해 자연스럽게 설명하되, **자기소개 형식이나 명령문, 메타발언 없이** 인물의 특징과 생활습관을 드러내 주세요.

[사용자 정보]
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

[생활 습관]
"""
    for section in user["lifestyle"]:
        prompt += f"- {section['title']}\n"
        for item in section["items"]:
            prompt += f"  • {item['label']}: {item['value']}\n"

    prompt += f"""

📋 {user['name']} 님에 대한 요약:  
사용자 정보 출력 (5문장)
"""
    return prompt.strip()

for user in users:
    prompt = make_prompt(user)
    result = generator(prompt, max_new_tokens=250, do_sample=True, temperature=0.7)[0]["generated_text"]
    
    summary = result.split("줄글 요약:")[-1].strip()
    print(f"\n📝 {user['name']} 님에 대한 요약:\n{summary}\n")
