python setup.py sdist
echo "twine upload $CURRENT_DIR/dist/$(ls -rt dist | tail -1)"
