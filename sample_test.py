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
        "당신은 사용자의 생활 스타일 정보를 바탕으로 한 문단 소개를 생성하는 AI입니다.\n"
        "다음 조건을 반드시 지키세요:\n"
        "1. 입력된 정보만 사용하고, 추측하거나 과장하지 마세요.\n"
        "2. 표현은 자연스럽고 부드럽게 이어지도록 구성하세요.\n"
        "3. 모든 주요 정보(거주지, 직업, 성격, MBTI, 취미, 생활습관 등)를 빠짐없이 포함하세요.\n"
        "4. 한 문단 분량으로 요약하되, 너무 간결하거나 생략하지 마세요.\n"
        "5. 부정확한 표현(예: '거의 하지 않음', '허용되지 않음')은 사용하지 마세요.\n"
    )

    few_shot_example = (
        "### 입력:\n"
        "김하늘님(29세)은 부산 해운대구에 거주하는 디자이너로, 조용하고 차분한 성격입니다.\n"
        "MBTI는 INFJ이며, 독서, 영화 감상, 요가를 즐깁니다.\n"
        "비흡연자이며 음주는 하지 않습니다.\n"
        "식사는 규칙적으로 하며, 주방은 자주 사용하고 주 3~4회 요리합니다.\n"
        "청결 수준은 높으며, 청소는 주 5회 이상 합니다. 공용공간도 깔끔하게 유지합니다.\n"
        "소음에 민감하며, 조용한 환경을 선호합니다. 기상은 오전 6시, 취침은 오후 11시입니다.\n"
        "반려동물은 허용하지 않으며, 알레르기가 있습니다.\n"
        "### 출력:\n"
        "김하늘님(29세)은 부산 해운대구에 거주하는 디자이너로, 조용하고 차분한 성격을 지닌 INFJ 유형입니다. 독서, 영화 감상, 요가를 즐기며 혼자만의 시간을 소중히 여깁니다. 비흡연자이며 음주는 하지 않으며, 식사는 규칙적으로 하고 주방을 자주 사용해 주 3~4회 요리합니다. 청결 수준이 높아 주 5회 이상 청소하며, 공용공간도 항상 깔끔하게 유지합니다. 소음에 민감해 조용한 환경을 선호하고, 오전 6시에 기상하여 오후 11시에 취침하는 규칙적인 생활을 유지합니다. 반려동물은 허용하지 않으며, 알레르기가 있습니다.\n\n"
    )

    full_prompt = f"{system_prompt}\n{few_shot_example}### 입력:\n{prompt}\n### 출력:\n"

    inputs = tokenizer(
        full_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024
    ).to(model.device)

    if "token_type_ids" in inputs:
        del inputs["token_type_ids"]

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

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return generated.split("### 출력:")[-1].strip()


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
