docker build --target sloth-test -t sloth-test .
docker run --rm --name test-app -v $(pwd)/test/enderecos:/app -w /app sloth-test python manage.py test
