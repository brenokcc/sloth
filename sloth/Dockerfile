FROM python:alpine as sloth-base
RUN apk add zlib-dev jpeg-dev build-base git libffi-dev
ADD requirements.txt /requirements.txt
RUN pip install -q --no-cache-dir -r /requirements.txt

FROM sloth-base as sloth-test
RUN pip install -q --no-cache-dir selenium
RUN apk add firefox-esr
RUN ln -sfn /usr/bin/firefox-esr /usr/bin/firefox
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux32.tar.gz
RUN tar -xf geckodriver-v0.32.0-linux32.tar.gz
RUN chmod +x geckodriver
RUN mv geckodriver /usr/local/bin/
ENV PYTHONPATH=/var/site-packages
ADD sloth $PYTHONPATH/sloth

FROM sloth-base as sloth-src
ENV PYTHONPATH=/var/site-packages
ADD . $PYTHONPATH/sloth

FROM minidocks/weasyprint as sloth-weasyprint
ADD ./cloud/printer.py /opt/printer.py
EXPOSE 8888
ENTRYPOINT ["python", "/opt/printer.py"]

FROM sloth-base as sloth
RUN pip install --no-cache-dir django-sloth
