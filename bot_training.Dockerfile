# syntax=docker/dockerfile:1
FROM python:3.8.8-slim-buster
WORKDIR /alliance_bot

ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="VENV/bin:$PATH"

COPY ./requirements.txt ./requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./messages ./messages 
COPY ./telegram_training_bot.py ./telegram_training_bot.py
COPY ./alliance.py ./alliance.py 
COPY ./.env ./.env
CMD ["python", "./telegram_training_bot.py"]
