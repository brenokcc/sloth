import json
from datetime import date, datetime
from django.test import TestCase
from dms2.test import ServerTestCase
from .models import Estado, Municipio, Endereco, Servidor, Ferias, Frequencia
from django.contrib.auth.models import Group


def loaddata():
    rn = Estado.objects.create(sigla='RN')
    natal = Municipio.objects.create(nome='Natal', estado=rn)
    endereco = Endereco.objects.create(
        logradouro='Centro', numero=1, municipio=natal
    )
    servidor = Servidor.objects.create(
        matricula='1799479', nome='Breno Silva', cpf='047.704.024-14', endereco=endereco
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
        servidor = Servidor.objects.first()
        self.log(Group.objects.first().serialize())
        self.log(Group.objects.serialize())
        self.log(Ferias.objects.all().serialize())
        self.log(servidor.serialize())
        self.log(servidor.serialize('get_dados_gerais'))
        self.log(servidor.serialize('get_dados_recursos_humanos'))
        self.log(servidor.serialize('get_endereco'))
        self.log(Servidor.objects.serialize())
        self.log(Servidor.objects.serialize('com_endereco'))


class ApiTestCase(ServerTestCase):

    def test(self):
        loaddata()
        self.debug = True
        self.get('/api/base/servidor/1/')
        self.get('/api/base/servidor/1/get_ferias/')
        self.get('/api/base/servidor/1/get_ferias/1-2/alterarferias/')
        self.get('/api/base/servidor/')
        self.get('/api/base/servidor/sem_endereco/')
        self.get('/api/base/servidor/com_endereco/1/ativarservidor/')
