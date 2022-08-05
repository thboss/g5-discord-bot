FROM python:3-alpine

RUN apk add libpq-dev build-base gettext jpeg-dev zlib-dev

WORKDIR /G5Bot
COPY . .
RUN pip3 install -r requirements.txt

CMD ls -la
CMD envsubst < /G5Bot/.env.template > /G5Bot/.env && \
    python3 migrate.py up && \
    python3 launcher.py