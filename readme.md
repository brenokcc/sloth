# Sloth - Take your time!

**Sloth** is an extension of *Django framework* aimed at the fast development of
web applications. It used metadate provided in the model classes to generate
the backend (REST API) and the frontend (Web interface).

![Kiku](sloth/api/static/images/logo.png)

The main functionalities offered by the framework are:

- Automatic generation of admin interface (listing, adding, editing, deleting and visualization of objects)
- Object-level access control based on roles and scopes
- Creation of applicaton dashboard
- Asynchronous tasks
- Responsive interface

## Installation

### Development

> pip install git+https://github.com/brenokcc/sloth.git#egg=sloth

### Production

> pip install sloth-framework

## Create Project 

> mkdir <project-name> OR git clone <repository-url> <project-name>
>
> cd <project-name>
>
> python -m sloth

## Docker

### Build

> python -m sloth build

### Run
> docker run -it --rm --name app -p 8000:8000 -v $(pwd):/app -w /app sloth sh


