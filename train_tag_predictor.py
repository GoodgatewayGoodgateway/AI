import json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report

# === 1. 데이터 로딩 ===
with open("full_user_data.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# === 2. 사용자 데이터만 추출 (title 키 없는 것만) ===
user_data = [entry for entry in raw_data if "title" not in entry]

# === 3. 태그 후보 추출 (후반부 항목에서) ===
tag_items = []
for entry in raw_data:
    if 'title' in entry and 'items' in entry:
        for item in entry['items']:
            if item.get("value"):
                tag_items.append(item["value"])

unique_tags = sorted(set(tag_items))

# === 4. 입력 (X) & 출력 (y) 준비 ===
X_rows = []
y_rows = []

for user in user_data:
    lifestyle = user.get("lifestyle", {})
    x_row = {
        "age": user.get("age", 0),
        "job": user.get("job", ""),
        "mbti": user.get("mbti", ""),
        "smoking": user.get("smoking", ""),
        "drinking": user.get("drinking", ""),
        "dayNightType": lifestyle.get("dayNightType", ""),
        "cleanLevel": lifestyle.get("cleanLevel", ""),
        "noise": lifestyle.get("noise", ""),
    }
    X_rows.append(x_row)

    # 자동 태그 생성 로직
    tags = set()

    # 청결 태그
    if lifestyle.get("cleanLevel") == "상":
        tags.add("청결 수준: 상")
    elif lifestyle.get("cleanLevel") == "중간":
        tags.add("청결 수준: 중")
    elif lifestyle.get("cleanLevel") == "하":
        tags.add("청결 수준: 하")

    # 소음 태그
    if lifestyle.get("noise") == "낮음":
        tags.add("소음 민감도: 높음")
    elif lifestyle.get("noise") == "보통":
        tags.add("소음 민감도: 보통")
    else:
        tags.add("소음 민감도: 낮음")

    # 흡연
    if user.get("smoking") == "흡연":
        tags.add("흡연 가능")
    else:
        tags.add("비흡연 선호")

    # 음주
    drinking = user.get("drinking", "").strip()
    if "금주" in drinking:
        tags.add("금주")
    elif "가끔" in drinking:
        tags.add("가끔 음주")
    else:
        tags.add("음주")

    y_rows.append(tags)

# === 5. DataFrame 변환 및 전처리 ===
X_df = pd.DataFrame(X_rows)
X_encoded = pd.get_dummies(X_df)

mlb_tags = MultiLabelBinarizer()
y_encoded = pd.DataFrame(mlb_tags.fit_transform(y_rows), columns=mlb_tags.classes_)

# === 6. 학습 & 테스트 분리 ===
X_train, X_test, y_train, y_test = train_test_split(
    X_encoded, y_encoded, test_size=0.2, random_state=42
)

# === 7. 모델 학습 ===
model = MultiOutputClassifier(RandomForestClassifier(random_state=42))
model.fit(X_train, y_train)

# === 8. 평가 ===
y_pred = model.predict(X_test)
print("📊 태그 예측 성능:\n")
print(classification_report(y_test, y_pred, target_names=mlb_tags.classes_))

# === 9. 저장 옵션 (선택) ===
# import joblib
# joblib.dump(model, "tag_predictor_model.pkl")
# joblib.dump(mlb_tags, "tag_label_binarizer.pkl")
# joblib.dump(X_encoded.columns, "tag_input_columns.pkl")
