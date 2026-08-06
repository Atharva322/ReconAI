FROM python:3.12-slim

WORKDIR /app

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY apps/api /app/apps/api
COPY packages /app/packages

ENV PYTHONPATH=/app/apps/api:/app/packages/domain:/app/packages/extraction:/app/packages/benchmark

EXPOSE 8000

CMD ["uvicorn", "reconai_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
