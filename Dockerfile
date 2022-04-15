FROM python:alpine
RUN apk add zlib-dev jpeg-dev build-base
RUN pip install sloth