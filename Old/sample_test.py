# 딥러닝 기반 자연어 생성 모델을 이용한 인공지능 응용 개발 작업
# 사용된 모델 : KoAlpaca-Polyglot-5.8B
# 모델 다운로드 링크 : https://huggingface.co/beomi/KoAlpaca-Polyglot-5.8B

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def load_prompt(path="prompt_config.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

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

    # 디바이스 설정 추가
    if torch.cuda.is_available():
        device = torch.device("cuda")
        dtype = torch.float16
        print("CUDA GPU 사용 중..")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        dtype = torch.float32
        print("MPS(NPU) 사용 중..")
    else:
        device = torch.device("cpu")
        dtype = torch.float32
        print("CPU 사용 중..")

    # 모델 로드
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=dtype,
    ).to(device)

    return tokenizer, model, device

def generate_summary(prompt, tokenizer, model, device, max_new_tokens=256):
    system_prompt = load_prompt()

    full_prompt = f"{system_prompt}\n### 입력:\n{prompt}\n### 출력:\n"

    inputs = tokenizer(
        full_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024
    )

    inputs.pop("token_type_ids", None)
    inputs = {k: v.to(device) for k, v in inputs.items()}

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

    if "### 출력:" in generated:
        return generated.split("### 출력:")[-1].strip()
    else:
        return generated.strip()

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def main():
    model_path = "E:\KoAlpaca-Model\KoAlpaca-Polyglot-5.8B"
    user_list = load_json("user.json")

    tokenizer, model, device = load_model(model_path)

    for user in user_list:
        prompt = convert_to_prompt(user)
        print("\n[ 입력 프롬프트 ]:\n", prompt)
        print("\n[ 생성된 소개 문장 ]:\n", generate_summary(prompt, tokenizer, model, device))
        print("=" * 100)

if __name__ == "__main__":
    main()
