VERSION=$(cat setup.py | grep version | sed "s/',//" | sed "s/.*='//")
echo "Building brenokcc/sloth:$VERSION"
docker build --target sloth -t brenokcc/sloth:$VERSION .
docker login -u brenokcc -p $DOCKERHUB_PASSWORD
docker push brenokcc/sloth:$VERSION
