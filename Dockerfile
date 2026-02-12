FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mbid_lookup.py .

CMD ["python", "mbid_lookup.py"]
