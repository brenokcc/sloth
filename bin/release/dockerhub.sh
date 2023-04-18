CURRENT_VERSION=$(cat setup.py | grep version | sed "s/',//" | sed "s/.*='//")
LAST_VERSION_JSON=$(curl -s 'https://hub.docker.com/v2/repositories/brenokcc/sloth/tags/?page_size=1')
DOCKERHUB_VERSION=$(echo $LAST_VERSION_JSON | grep -o $CURRENT_VERSION)
echo "Current version: $CURRENT_VERSION"
echo "Dockerhub version: $DOCKERHUB_VERSION"
if [[ "$DOCKERHUB_VERSION" != "$CURRENT_VERSION" ]]; then
  echo "Building brenokcc/sloth:$VERSION"
  PYPI_VERSION=$(pip install sloth-framework==0.0.0 2>&1 >/dev/null | grep -o $CURRENT_VERSION)
  echo "PyPi version: $PYPI_VERSION"
  if [[ "$PYPI_VERSION" == "" ]]; then
    sleep 60;
  fi
  PYPI_VERSION=$(pip install sloth-framework==0.0.0 2>&1 >/dev/null | grep -o $CURRENT_VERSION)
  echo "PyPi version: $PYPI_VERSION"
  if [[ "$PYPI_VERSION" != "" ]]; then
    docker build -f sloth/Dockerfile --target sloth -t brenokcc/sloth:$CURRENT_VERSION .
    docker login -u brenokcc -p $DOCKERHUB_PASSWORD
    docker push brenokcc/sloth:$CURRENT_VERSION
  fi
fi
