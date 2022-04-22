# Sloth

![Kiku](sloth/admin/static/images/sloth.png)


## Installation

### Development

> pip install git+https://github.com/brenokcc/sloth.git#egg=sloth

### Production

> pip install django-sloth

## Create Project

> django-admin startproject <project-name>
>
> cd <project-name>
>
> python -m sloth configure
>
> python manage.py sync
>
> python manage.py createsuperuser
>
> python manage.py runserver

## Docker

### Build

> bin/build.sh

### Run
> docker run -it --rm --name app -p 8000:8000 -v $(pwd):/app -w /app sloth sh




