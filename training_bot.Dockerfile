# syntax=docker/dockerfile:1
FROM python:3.8.8
WORKDIR /alliance_bot

ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="VENV/bin:$PATH"

COPY ./requirements.txt ./requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./messages ./messages 
COPY ./telegram_alliance_bot.py ./telegram_alliance_bot.py
COPY ./alliance.py ./alliance.py 
CMD ["python", "./telegram_alliance_bot.py"]
