FROM python as sloth
ENV PYTHONPATH=/var/site-packages
RUN apt update
RUN apt install -y wkhtmltopdf
RUN pip install --no-cache-dir Django==4.1 requests==2.28.1 django-oauth-toolkit==2.1.0 xlwt==1.3.0 xlrd==1.2.0 Pillow==9.2.0 gunicorn==20.1.0 onetimepass==1.0.1 pdfkit==1.0.0
ADD . $PYTHONPATH/sloth


