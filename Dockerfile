FROM python:3.11-slim

WORKDIR /app

COPY secretary/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY secretary/ .

CMD ["python", "bot.py"]
