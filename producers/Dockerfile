FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only what we need first (speeds rebuilds)
COPY producers/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy producer code
COPY producers/ ./

# Run as non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Default command (can be overwritten in compose)
CMD ["python", "producer.py"]