# 딥러닝 기반 자연어 생성 모델을 이용한 인공지능 응용 개발 작업
# 사용된 모델 : KoAlpaca-Polyglot-5.8B
# 모델 다운로드 링크 : https://huggingface.co/beomi/KoAlpaca-Polyglot-5.8B

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def convert_to_prompt(user):
    lines = []
    lines.append(f"{user['name']}님({user['age']}세)은 {user['location']}에 거주하는 {user['job']}으로, {user['introduction']}")
    lines.append(f"MBTI는 {user['mbti']}이며, {', '.join(user['interests'])}을(를) 즐깁니다.")
    lines.append(f"{user['smoking']}이고 {user['drinking']}합니다.")
    lines.append(user['idealRoommate'])

    for section in user["lifestyle"]:
        items = [f"{item['label']}은 {item['value']}" for item in section["items"]]
        lines.append(" / ".join(items))

    return "\n".join(lines)

def load_model(model_path):
    print("모델과 토크나이저 로드 중...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    return tokenizer, model

def generate_summary(prompt, tokenizer, model, max_new_tokens=256):
    system_prompt = (
        "당신은 사용자의 생활 스타일 정보를 바탕으로 줄글 소개를 생성하는 AI입니다.\n"
        "다음 조건을 반드시 지키세요:\n"
        "1. 입력된 정보만 사용하고, 추측하거나 과장하지 마세요.\n"
        "2. 표현은 자연스럽고 부드럽게 이어지도록 구성하세요.\n"
        "3. 모든 주요 정보(거주지, 직업, 성격, MBTI, 취미, 생활습관 등)를 빠짐없이 포함하세요.\n"
        "4. 한 문단 분량으로 요약하되, 너무 간결하거나 생략하지 마세요.\n"
        "5. 부정확한 표현(예: '거의 하지 않음', '허용되지 않음')은 사용하지 마세요.\n"
    )

    # 프롬프트 구성
    full_prompt = f"{system_prompt}\# 입력:\n{prompt}\n# 출력:\n"

    # 토크나이즈
    inputs = tokenizer(
        full_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024  # 모델의 max input 제한 고려
    ).to(model.device)

    # token_type_ids 제거 (KoAlpaca-Polyglot 계열에서는 필요 없음)
    inputs.pop("token_type_ids", None)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    # 출력 디코딩
    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 결과 후처리: '### 출력:' 이후만 가져오되, 없을 경우 전체 사용
    if "### 출력:" in generated:
        return generated.split("### 출력:")[-1].strip()
    else:
        return generated.strip()

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def main():
    model_path = "./KoAlpaca-Polyglot-5.8B"
    user_list = load_json("user.json")

    tokenizer, model = load_model(model_path)

    for user in user_list:
        prompt = convert_to_prompt(user)
        print("\n🧾 [입력 프롬프트]:\n", prompt)
        print("\n📝 [생성된 소개 문장]:\n", generate_summary(prompt, tokenizer, model))
        print("=" * 100)

if __name__ == "__main__":
    main()
