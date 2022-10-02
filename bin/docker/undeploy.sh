set -axe
ROOT_DIR=$1
APP_NAME=$(basename "$ROOT_DIR")
docker stop $APP_NAME
rm /etc/nginx/conf.d/$APP_NAME.conf
nginx -s reload
