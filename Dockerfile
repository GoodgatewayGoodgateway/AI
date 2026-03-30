FROM python:3.10-slim

# 시스템 의존성 (mysql-connector 빌드에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 레이어 캐시 최적화 — requirements만 먼저 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

EXPOSE 8888

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
