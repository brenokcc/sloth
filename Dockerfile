FROM python:alpine
RUN apk add zlib-dev jpeg-dev build-base git libffi-dev
RUN pip install --no-cache-dir -e git+https://github.com/brenokcc/sloth.git#egg=sloth