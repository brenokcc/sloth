import os
from setuptools import find_packages, setup

root_dir = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir))

with open(os.path.join(root_dir, 'requirements.txt')) as file:
    requirements = file.read().strip().splitlines()

os.chdir(root_dir)

setup(
    name='django-sloth',
    version='0.0.44',
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        'dev': [],
        'production': [],
    },
    include_package_data=True,
    license='BSD License',
    description='Metadata-based web framework for the development of management information systems',
    long_description='',
    url='http://sloth.aplicativo.click/',
    author='Breno Silva',
    author_email='brenokcc@yahoo.com.br',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
