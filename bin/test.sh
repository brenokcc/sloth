docker build -f sloth/Dockerfile --target sloth-test -t sloth-test sloth
APPS=${1:-"lugares erp papeis petshop"}
for APP in $APPS; do
  docker run --rm --name test-app -v "$(pwd)/test/$APP:/app" -w /app sloth-test python manage.py test
done
