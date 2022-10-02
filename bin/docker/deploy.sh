set -axe
ROOT_DIR=$1
APP_NAME=$(basename "$ROOT_DIR")
DOMAIN="aplicativo.space"
CERTIFICATE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
CERTIFICATE_KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
docker run --rm --name $APP_NAME --memory="256m" --memory-swap="512m" --cpus="1.0" -p 80 -v "$ROOT_DIR":/app -w /app -d sloth-src gunicorn -b 0.0.0.0:80 $APP_NAME.wsgi:application -w 1 -t 360 --log-level=info
docker exec $APP_NAME python manage.py migrate
docker exec $APP_NAME python manage.py collectstatic --noinput
PORT=$(docker inspect --format '{{ (index (index .NetworkSettings.Ports "80/tcp") 0).HostPort }}' $APP_NAME)
printf "
server {
 listen 80;
 listen 443 ssl;
 server_name $APP_NAME.$DOMAIN s1.localhost;
 ssl_certificate $CERTIFICATE;
 ssl_certificate_key $CERTIFICATE_KEY;
 location /media { alias $ROOT_DIR/media;}
 location /static { alias $ROOT_DIR/static;}
 location / {proxy_pass http://127.0.0.1:$PORT;}
}
" > /etc/nginx/conf.d/$APP_NAME.conf
nginx -s reload

