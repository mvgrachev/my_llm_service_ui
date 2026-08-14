FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "start_server.py"]
