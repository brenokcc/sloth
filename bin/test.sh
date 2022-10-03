docker build --target sloth-test -t sloth-test .
APPS=${1:-"erp papeis petshop"}
for APP in $APPS; do
  echo docker run --rm --name test-app -v "$(pwd)/test/$APP:/app" -w /app sloth-test python manage.py test
done
