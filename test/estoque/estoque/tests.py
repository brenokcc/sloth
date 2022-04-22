# -*- coding: utf-8 -*-

import json
from .models import Pessoa, Rede
from sloth.api.models import User
from django.test import TestCase


def log(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))

class ModelTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        self.debug = True
        super().__init__(*args, **kwargs)

    def log(self, data):
        if self.debug:
            print(json.dumps(data, indent=4, ensure_ascii=False))

    def test(self):
        p1 = Pessoa.objects.create(nome='p1', email='p1.mail.com')
        p2 = Pessoa.objects.create(nome='p2', email='p2.mail.com')
        p3 = Pessoa.objects.create(nome='p3', email='p3.mail.com')
        r1 = Rede.objects.create(nome='rede-1', gerente=p1)
        r1.post_save()
        r2 = Rede.objects.create(nome='rede-2', gerente=p2)
        r2.post_save()
        u1 = User.objects.get(username='p1.mail.com')
        self.assertEqual(Rede.objects.all().count(), 2)
        self.assertEqual(Rede.objects.all().apply_role_lookups(u1).count(), 1)
