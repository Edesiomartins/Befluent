FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN addgroup --system fluentia && adduser --system --ingroup fluentia fluentia
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x scripts/entrypoint.sh && chown -R fluentia:fluentia /app
USER fluentia
EXPOSE 8000
ENTRYPOINT ["./scripts/entrypoint.sh"]
