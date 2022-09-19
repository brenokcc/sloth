docker build --target sloth-test -t sloth-test .
APPS=${1:-"erp papeis enderecos petshop"}
for APP in $APPS; do
  docker run --rm --name test-app -v "$(pwd)/test/$APP:/app" -w /app sloth-test python manage.py test
done
