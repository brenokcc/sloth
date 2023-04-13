#!/usr/bin/env bash
set -axe

WORKDIR="/Users/breno/Documents/Workspace/sloth/test"
PROJECT_NAME="$2"
CONTAINER_NAME="$PROJECT_NAME-web-1"
FILE="$WORKDIR/$PROJECT_NAME/docker-compose.yml"

if [[ $1 == "start" ]]; then
  echo "Starting nginx..."
    docker network create sloth
    docker run --name nginx -d --rm -p 80:80 -v $(pwd):/etc/nginx/conf.d --network sloth nginx
    docker run --name deployer -d --rm -p 9999:9999 -v $(pwd):/opt --network sloth python /opt/deployer.py
fi

if [[ $1 == "deploy" ]]; then
	echo "Deploying $PROJECT_NAME..."
	docker-compose -f $FILE up --detach
	docker network connect sloth $CONTAINER_NAME
	docker exec nginx sh -c "echo 'server {server_name $PROJECT_NAME.local.aplicativo.click; location / { proxy_pass http://$CONTAINER_NAME:8000; }}' > /etc/nginx/conf.d/$PROJECT_NAME.conf"
	docker exec nginx nginx -s reload
fi

if [[ $1 == "update" ]]; then
  echo "Updating $PROJECT_NAME..."
fi


if [[ $1 == "undeploy" ]]; then
  echo "Undeploying $PROJECT_NAME..."
  docker network disconnect sloth $CONTAINER_NAME
  docker exec nginx sh -c "rm /etc/nginx/conf.d/$PROJECT_NAME.conf"
  docker exec nginx nginx -s reload
  docker-compose -f $FILE down
fi


if [[ $1 == "destroy" ]]; then
  echo "Destroying $PROJECT_NAME..."
fi

if [[ $1 == "stop" ]]; then
  echo "Stoping nginx..."
  docker stop nginx
  docker stop deployer
  docker network rm sloth
fi
