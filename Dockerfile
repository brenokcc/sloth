FROM python:alpine as sloth-base
RUN apk add zlib-dev jpeg-dev build-base git libffi-dev
ADD requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

FROM sloth-base as sloth-test
RUN pip install --no-cache-dir selenium
RUN apk add firefox-esr=91.13.0-r0
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux32.tar.gz
RUN tar -xvf geckodriver-v0.31.0-linux32.tar.gz
RUN chmod +x geckodriver
RUN mv geckodriver /usr/local/bin/
ENV PYTHONPATH=/var/site-packages
ADD sloth $PYTHONPATH/sloth

FROM sloth-base as sloth-src
ENV PYTHONPATH=/var/site-packages
ADD sloth $PYTHONPATH/sloth

FROM sloth-base as sloth
RUN pip install --no-cache-dir django-sloth
