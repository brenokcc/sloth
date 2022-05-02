python setup.py sdist
echo "twine upload dist/$(ls -rt dist | tail -1)"
