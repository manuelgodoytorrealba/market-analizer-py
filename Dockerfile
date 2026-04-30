FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -e .
RUN python -m playwright install chromium firefox

CMD ["python", "-m", "scripts.cli", "serve"]