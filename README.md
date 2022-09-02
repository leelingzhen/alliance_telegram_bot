# A training attendance manager that uses python-telegram-bot and google sheets api

## Setup
using Docker is recommended. 
install [Docker] (https://docs.docker.com/engine/install/ubuntu/)
install [Docker-compose] (https://docs.docker.com/compose/install/)

in docker-compose.yml, use the following to run the containers
```
  adminbot:
    image: leelingzhen/telegram-admin-attendance-bot
    container_name: admin_attendance_bot
    volumes:
      - $DOCKERDIR/alliance_telegram_bot/.secrets:/alliance_bot/.secrets
    environment:
      - PUID=$PUID
      - PGID=$PGID
      - TZ=$TZ

  trainingbot:
    image: leelingzhen/telegram-attendance-bot
    container_name: training_attendance_bot
    volumes:
      - $DOCKERDIR/alliance_telegram_bot/.secrets:/alliance_bot/.secrets
    environment:
      - PUID=$PUID
      - PGID=$PGID
      - TZ=$TZ
```
relevant enviromental variables can be defined in a .env file

## Stopping containers
containers must be killed if not python script my persist running which will conflict with a new instance of telegram bot. 
in that case rebuild containers or revoke bot access token.
containers can be stopped by
```
docker stop training_attendance_bot
docker stop admin_attendance_bot
```
