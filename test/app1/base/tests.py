# -*- coding: utf-8 -*-

import json
from datetime import date, datetime
from django.contrib.auth.models import Group
from django.test import TestCase
from oauth2_provider.generators import generate_client_id

from dms2.test import ServerTestCase
from .models import Estado, Municipio, Endereco, Servidor, Ferias, Frequencia
from dms2 import utils


def log(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))


def loaddata():
    rn = Estado.objects.create(sigla='RN')
    natal = Municipio.objects.create(nome='Natal', estado=rn)
    endereco = Endereco.objects.create(
        logradouro='Centro', numero=1, municipio=natal
    )
    servidor = Servidor.objects.create(
        matricula='1799479', nome='Breno Silva',
        cpf='047.704.024-14', data_nascimento=date(1984, 8, 27),
        endereco=endereco, naturalidade=natal
    )
    Ferias.objects.create(servidor=servidor, ano=2020, inicio=date(2020, 1, 1), fim=date(2020, 1, 31))
    Ferias.objects.create(servidor=servidor, ano=2021, inicio=date(2021, 8, 1), fim=date(2021, 8, 31))
    Frequencia.objects.create(servidor=servidor, horario=datetime.now())
    Group.objects.create(name='Administrador')


class ModelTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        self.debug = True
        super().__init__(*args, **kwargs)

    def log(self, data):
        if self.debug:
            print(json.dumps(data, indent=4, ensure_ascii=False))

    def test(self):
        loaddata()
        self.log(Municipio.objects.first().serialize(wrap=True, verbose=True))
        self.log(Municipio.objects.count('estado').serialize())
        self.log(Municipio.objects.all().serialize(wrap=True, verbose=True))
        servidor = Servidor.objects.first()
        self.log(servidor.serialize(wrap=True, verbose=True))
        self.log(Servidor.objects.count('naturalidade').serialize())
        self.log(Servidor.objects.count('naturalidade', 'ativo').serialize())
        self.log(Servidor.objects.serialize(wrap=True, verbose=True))

        self.log(servidor.get_ferias().count('ano').serialize())
        self.log(servidor.serialize(wrap=True, verbose=True))
        self.log(Servidor.objects.com_endereco().serialize(wrap=True, verbose=True))
        self.log(Group.objects.first().serialize())
        self.log(Group.objects.all().serialize())
        self.log(Ferias.objects.all().serialize())

        servidor = Servidor.objects.first()
        self.log(servidor.serialize())
        self.log(servidor.serialize('get_dados_gerais'))
        self.log(servidor.serialize('get_dados_recursos_humanos'))
        self.log(servidor.serialize('get_endereco'))
        self.log(Servidor.objects.serialize())
        self.log(Servidor.objects.com_endereco().serialize())
        self.log(Servidor.objects.sem_endereco().serialize())


class ApiTestCase(ServerTestCase):

    def test(self):
        loaddata()
        self.debug = True
        self.create_user('user', '123')
        self.create_user('admin', '123', True)

        # not authenticated
        self.get('/api/auth/group/add/', status_code=403)

        # not authorized
        self.login('user', '123')
        self.get('/api/auth/group/add/', status_code=401)
        self.get('/api/base/servidor/1/', status_code=401)
        self.get('/api/base/servidor/1/get_dados_gerais/', status_code=401)
        self.post(
            '/api/base/servidor/1/get_dados_gerais/corrigirnomeservidor/',
            dict(nome='Emanoel'), status_code=401
        )
        self.post(
            '/api/base/servidor/1/get_ferias/1-2/alterarferias/',
            dict(inicio='01/06/2020', fim='01/07/2020'), status_code=401
        )

        # authenticated and authorized
        self.login('admin', '123')

        self.get('/api/auth/group/')
        self.post('/api/auth/group/add/', data=dict(name='Operador'))
        self.get('/api/auth/group/1/')
        self.get('/api/auth/group/1/edit/')
        self.post('/api/auth/group/1/edit/', data=dict(name='Gerente'))
        self.get('/api/auth/group/1/delete/')
        # self.post('/api/auth/group/1/delete/')

        self.get('/api/base/servidor/')
        self.get('/api/base/servidor/ativos/')
        self.post('/api/base/servidor/1/inativarservidores/')
        self.get('/api/base/servidor/ativos/')

        self.get('/api/base/servidor/1/')
        self.get('/api/base/servidor/1/get_dados_gerais/')
        self.post('/api/base/servidor/1/get_dados_gerais/corrigirnomeservidor/', dict(nome='Emanoel'))
        self.get('/api/base/servidor/1/get_dados_gerais/')
        self.get('/api/base/servidor/1/get_ferias/')
        self.post('/api/base/servidor/1/get_ferias/1-2/alterarferias/', dict(inicio='01/06/2020', fim='01/07/2020'))
        self.get('/api/base/servidor/1/get_ferias/')


class MenuTestCase(TestCase):

    def test(self):
        items = utils.load_menu(None)
        log(items)


class Oauth2TestCase(ServerTestCase):

    def test(self):
        self.debug = True
        Estado.objects.create(sigla='RN')
        Estado.objects.create(sigla='PB')
        admin = self.create_user('admin', '123', True)
        self.login('admin', '123')
        data = dict(name='public', description='Publica Data')
        self.post('/api/dms2/scope/add/', data=data)
        data = dict(
            redirect_uris='', client_type='confidential',
            authorization_grant_type='password', name='App01',
            skip_authorization=True, user=admin.pk, client_id=generate_client_id(),
            default_scopes=[1], available_scopes=[1]
        )
        self.get('/api/dms2/application/')
        self.post('/api/dms2/application/add/', data=data)
        app = self.get('/api/dms2/application/1/')
        self.logout()

        data = dict(
            client_id=app['access_data']['client_id']['value'],
            client_secret=app['access_data']['client_secret']['value'],
            grant_type=app['access_data']['authorization_grant_type']['value'],
            username=admin.username,
            password='123',
            scope='public'
        )
        self.get('/api/base/estado/', status_code=403)
        response = self.post('/o/token/', data=data)
        self.authorize(response['access_token'])
        self.get('/api/base/estado/')
