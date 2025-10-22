from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 사용 가능한 모델 테스트
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "안녕하세요. OpenAI API가 정상적으로 작동하는지 테스트합니다."}
    ],
    max_tokens=50
)

print("OpenAI API 연결 성공!")
print(f"응답: {response.choices[0].message.content}")