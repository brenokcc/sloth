from django.test import TestCase
from .models import *
from sloth.api.models import Role, User


class AppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}

    def setUp(self):
        for nome in ('f1', 'f2', 'f3', 'f4', 'f5'):
            self.data[nome] = Funcionario.objects.create(nome=nome)
        for nome in ('r1', 'r2'):
            self.data[nome] = Rede.objects.create(nome=nome)
        self.data['d1'] = Diretor.objects.create(nome='d1', rede=self.data['r1'])
        self.data['d2'] = Diretor.objects.create(nome='d2', rede=self.data['r2'])

        self.data['l1'] = Loja.objects.create(nome='l1', rede=self.data['r1'], gerente=self.data['f1'])
        self.data['l1'].funcionarios.add(self.data['f2'])
        self.data['l1'].persist()

    def debug(self):
        for user in User.objects.all():
            print(user)
            print('NAME|KEY|TYPE|VALUE')
            for role in user.roles.all():
                print('{}|{}|{}|{}'.format(role.name, role.scope_key, role.scope_type, role.get_scope_value()))
            print('---')

    def test(self):
        self.debug()
        self.assertEqual(User.objects.count(), 7)
        self.assertEqual(Role.objects.count(), 13)

        user = User.objects.get(username='f1')
        qs = Funcionario.objects.filter_by_scope('Funcionário').apply_role_lookups(user)
        self.assertEqual(qs.count(), 1)

        user = User.objects.get(username='d1')
        qs = Rede.objects.filter_by_scope('Diretor', pk='rede').apply_role_lookups(user)
        self.assertEqual(qs.count(), 1)