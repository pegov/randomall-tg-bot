FROM python:3.11

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 1

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PYTHONPATH=./

COPY randomall_tg_bot ./randomall_tg_bot
COPY .env .

CMD [ "python", "randomall_tg_bot/main.py"]
