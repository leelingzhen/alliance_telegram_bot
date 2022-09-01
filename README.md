# A training attendance manager that uses python-telegram-bot and google sheets api

## Setup
for docker implementation, build images separately for admin and telegram bot using 
```
docker build -t admin_bot .
docker build -t alliance_bot .
```

in docker-compose.yml, use the following to run the containers
```
  adminbot:
    image: admin_bot
    container_name: alliance_admin_telegram_bot
    volumes:
      - $DOCKERDIR/alliance_telegram_bot:/alliance_bot
    environment:
      - PUID=$PUID
      - PGID=$PGID
      - TZ=$TZ

  trainingbot:
    image: alliance_bot
    container_name: alliance_training_telegram_bot
    volumes:
      - $DOCKERDIR/alliance_telegram_bot:/alliance_bot
    environment:
      - PUID=$PUID
      - PGID=$PGID
      - TZ=$TZ
```
## Stopping containers
containers must be killed if not python script my persist running which will conflict with a new instance of telegram bot. 
in that case rebuild containers or revoke bot access token.
containers can be stopped by
```
docker kill alliance_training_telegram_bot
docker kill alliance_admin_telegram_bot
```
