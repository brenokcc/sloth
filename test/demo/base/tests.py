import json
from datetime import date, datetime
from django.test import TestCase

from dms2.utils import scan
from .models import Estado, Municipio, Endereco, Servidor, Ferias, Frequencia
from django.contrib.auth.models import Group


class DefaultTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        self.debug = True
        super().__init__(*args, **kwargs)

    def log(self, data):
        if self.debug:
            print(json.dumps(data, indent=4, ensure_ascii=False))

    def test_queryset(self):
        Estado.objects.create(sigla='RN')
        Estado.objects.create(sigla='PB')
        self.log(Estado.objects.all().search('sigla').filters('sigla').get())

    def test_models(self):
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

        self.assertEqual(Servidor.objects.com_endereco().count(), 1)
        self.assertEqual(Servidor.objects.sem_endereco().count(), 0)

        group = Group.objects.create(name='Administrador')

        # self.log(group.serialize())
        # self.log(Group.objects.serialize())
        # self.log(Ferias.objects.all().serialize())
        # self.log(servidor.serialize())
        self.log(servidor.serialize('dados_gerais'))
        # self.log(servidor.serialize('dados_recursos_humanos'))
        # self.log(servidor.serialize('endereco'))
        # self.log(Servidor.objects.serialize())
        # self.log(Servidor.objects.serialize('com_endereco'))

        # self.log(scan())
        # import pdb; pdb.set_trace()

