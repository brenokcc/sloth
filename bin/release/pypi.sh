CURRENT_VERSION=$(cat setup.py | grep version | sed "s/',//" | sed "s/.*='//")
REMOTE_VERSION=$(pip install django-sloth==0.0.0 2>&1 >/dev/null | grep -o $CURRENT_VERSION)
echo $REMOTE_VERSION $CURRENT_VERSION
if [[ "$REMOTE_VERSION" != "$CURRENT_VERSION" ]]; then
  pip install twine
  python setup.py sdist
  twine upload "dist/$(ls -rt dist | tail -1)" -u brenokcc -p $PIP_PASSWORD
fi
