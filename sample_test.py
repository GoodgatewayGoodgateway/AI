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
    system_prompt = "당신은 친절하고 요약을 잘하는 AI입니다. 아래의 정보를 자연스럽게 소개문장으로 정리하세요.\n"
    full_prompt = f"{system_prompt}### 입력:\n{prompt}\n### 출력:\n"

    inputs = tokenizer(full_prompt, return_tensors="pt", padding=True, truncation=True).to(model.device)

    # token_type_ids 제거
    if "token_type_ids" in inputs:
        del inputs["token_type_ids"]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
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
