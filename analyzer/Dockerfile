FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY analyzer.py .

COPY tests ./tests

RUN mkdir -p /incidents

EXPOSE 8001

CMD ["python", "analyzer.py"]
