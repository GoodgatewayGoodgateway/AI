# 1. 무슨 AI를 쓸 것인가?

이거에 대해서 생각을 많이하고 있다. AI라는 것이 많이 해보지 않았고 난 오히려 벡엔드나 프론트를 더 했기 때문이다.

---

그래도 무적정 GPT한테 물어보기는 그러니 미래 유망 시간에 배웠던 텐서플로우를 활용해보려고 한다.

일단 내가 만들 기능을 한번 정리 해보았다. </br>

1. 유저 데이터에 있는 정보들을 활용하여 자동으로 룸메이트 메칭에서 자신과 성향이 같은 사람을 태그를 맞추어 검색하여 찾아주는 것을 해야함.

2. (아직 없음.)

---

**유저 데이터 예시:**

```js
const users = [
    {
        id: 18,
        name: "이태영",
        age: 26,
        job: "영업 사원",
        introduction: "에너지가 넘치고 사람 만나는 걸 좋아합니다.",
        location: "서울시 서대문구",
        mbti: "ESFP",
        interests: ["사교모임", "피트니스", "카페", "여행"],
        idealRoommate: "친근하고 외향적인 분과 잘 지낼 수 있어요.",
        smoking: "비흡연",
        drinking: "가끔 음주",
        lifestyle: [
            {
                title: "🍽️ 식생활 & 주방 관련",
                items: [
                    { label: "식사 시간", value: "규칙적" },
                    { label: "주방 사용", value: "가끔 사용" },
                    { label: "요리 빈도", value: "주 1-2회" }
                ]
            },
            {
                title: "🧹 청결 및 정리 습관",
                items: [
                    { label: "청결 수준", value: "중" },
                    { label: "청소 주기", value: "주 3회 이상" },
                    { label: "공용공간 관리", value: "보통" }
                ]
            },
            {
                title: "🔊 소음 민감도",
                items: [
                    { label: "소음 민감도", value: "보통" },
                    { label: "취침시 소음", value: "조용한 환경 선호" },
                    { label: "음악/TV 볼륨", value: "적당히" }
                ]
            },
            {
                title: "⏰ 생활 리듬",
                items: [
                    { label: "기상 시간", value: "오전 7시" },
                    { label: "취침 시간", value: "오전 12시" }
                ]
            },
            {
                title: "🐾 반려동물 허용",
                items: [
                    { label: "반려동물 허용 여부", value: "부분 허용" },
                    { label: "반려동물 종류", value: "고양이" },
                    { label: "반려동물 알레르기", value: "없음" }
                ]
            }
        ]
    }
];
```

---

하지만, 처음부터 딥러닝을 시켜서 yolo로 모델을 만들어서 하기에는 너무 빡세고 힘들다. 고로 이미 만들어진 모델들을 적극 활용하여 만들어보는 길을 텍하였다.

일단 그거에 맞춰 GPT가 추천해준 AI 모델는 다음과 같다.

## 텍스트 분석용 – TF Hub + TensorFlow Text

**✅ 예: 감정 분석, 의도 파악, 요약 등**

* 모델 추천:
    * **BERT**: 감정 분석에 특화
    * **Universal Sentence Encoder**: 문장 의미 임베딩
    * **[ALBERT, DistilBERT]** 등 가볍고 빠름

사람이 적은 글을 보면 문장의 의미를 파악해서 태그를 지정해주어야 하기에 문장의 의미를 임베딩 하는 "Universal Sentence Encoder" 가 좋을거 같다고 생각하였다. 
