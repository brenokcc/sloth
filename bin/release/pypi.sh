pip install twine
python setup.py sdist
twine upload "dist/$(ls -rt dist | tail -1)" -u brenokcc -p $PIP_PASSWORD
