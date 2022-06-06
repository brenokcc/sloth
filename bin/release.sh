python setup.py sdist
twine upload "dist/$(ls -rt dist | tail -1)"
