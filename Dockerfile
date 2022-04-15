FROM python:alpine
RUN apk add zlib-dev jpeg-dev build-base git libffi-dev
RUN pip install --no-cache-dir git+https://github.com/brenokcc/sloth.git