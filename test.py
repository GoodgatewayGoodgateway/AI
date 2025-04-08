import tensorflow_hub as hub
import tensorflow as tf
from transformers import T5Tokenizer, TFT5ForConditionalGeneration

# ✅ 1. 모델 로딩 상태 표시
print("🔄 Universal Sentence Encoder 다운로드 및 로딩 중...")
use_model = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
print("✅ Universal Sentence Encoder 로딩 완료!\n")

print("🔄 T5 모델 다운로드 및 로딩 중...")
t5_tokenizer = T5Tokenizer.from_pretrained("t5-small")
t5_model = TFT5ForConditionalGeneration.from_pretrained("t5-small")
print("✅ T5 모델 로딩 완료!\n")

# ✅ 2. 입력 텍스트
print("📥 사용자 프로필 읽는 중...")
user_profile_text = """
이태영님은 26세의 서울시 서대문구에 거주하는 영업 사원으로, 에너지가 넘치고 사람을 만나는 것을 좋아하는 외향적인 성격의 소유자입니다. MBTI는 ESFP로, 활동적이고 사교적인 스타일이며, 사교 모임, 피트니스, 카페 탐방, 여행 등 사람들과 함께하는 활동에 관심이 많습니다.

흡연은 하지 않으며, 음주는 가끔 즐기는 편입니다. 이상적인 룸메이트로는 친근하고 외향적인 성격의 사람을 선호합니다.

생활 습관을 살펴보면, 식사 시간은 규칙적인 편이고, 주방은 가끔 사용하는 정도이며, 주 1~2회 정도 요리를 합니다. 청결에 있어서는 청소를 주 3회 이상 하며, 공용 공간도 평균적인 수준으로 관리하는 편입니다.

소음에 대해서는 보통 수준의 민감도를 가지고 있고, 취침 시에는 조용한 환경을 선호합니다. 음악이나 TV의 볼륨은 적당한 수준을 유지합니다.

생활 리듬은 규칙적이며, 보통 오전 7시에 기상하고 자정쯤 잠자리에 듭니다. 반려동물에 대해서는 부분 허용 입장이며, 특히 고양이를 허용하고, 반려동물 알레르기는 없습니다.
"""
print("✅ 사용자 프로필 불러오기 완료!\n")

# ✅ 3. USE 임베딩 처리 (실제로는 생성에 사용되진 않지만, 참고용)
print("📊 프로필 임베딩 중...")
embedding = use_model([user_profile_text])[0].numpy()
print("✅ 임베딩 완료!\n")

# ✅ 4. 생각 생성 함수
def generate_thought(text):
    print("🧠 생각 생성 중 (T5 모델 사용)...")
    prompt = f"이 사용자의 성향을 분석하여, 성향에 맞는 조언 또는 생각을 생성하세요: {text}"
    inputs = t5_tokenizer(prompt, return_tensors="tf", truncation=True, padding=True, max_length=512)
    outputs = t5_model.generate(inputs.input_ids, max_length=200, num_beams=5, no_repeat_ngram_size=2)
    result = t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("✅ 생각 생성 완료!\n")
    return result

# ✅ 5. 결과 출력
thought = generate_thought(user_profile_text)
print("🤖 생성된 맞춤형 생각:")
print(thought)
