import os
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

        self.data['l2'] = Loja.objects.create(nome='l2', rede=self.data['r2'], gerente=self.data['f4'])
        self.data['l2'].funcionarios.add(self.data['f5'])
        self.data['l2'].persist()

        self.data['l3'] = Loja.objects.create(nome='l3', rede=self.data['r1'], gerente=None)

        for i in range(1, 4):
            for j in range(1, 3):
                Produto.objects.create(nome='p{}l{}'.format(j, i), loja=self.data['l{}'.format(i)])

    def debug(self):
        for user in User.objects.all():
            print(user)
            print('NAME|KEY|TYPE|VALUE')
            for role in user.roles.all():
                print('{}|{}|{}|{}'.format(role.name, role.scope_key, role.scope_type, role.get_scope_value()))
            print('---')

    def test(self):
        if os.path.exists('/Users/breno'):
            self.debug()
        self.assertEqual(User.objects.count(), 7)
        self.assertEqual(Role.objects.count(), 17)

        user_f1 = User.objects.get(username='f1')
        qs = Funcionario.objects.role_lookups('Funcionário', pk='self').apply_role_lookups(user_f1)
        self.assertEqual(qs.count(), 1)

        user_f2 = User.objects.get(username='f2')
        qs = Loja.objects.role_lookups('Funcionário', pk='loja').apply_role_lookups(user_f2)
        print(qs)
        print('----')
        l1 = Loja.objects.get(nome='l1')
        print(l1.role_lookups('Funcionário', pk='loja').apply(user_f2))
        print(Produto.objects.role_lookups('Funcionário', loja='loja').apply_role_lookups(user_f2))
        p1l1 = Produto.objects.get(nome='p1l1')
        print(p1l1.role_lookups('Funcionário', loja='loja').apply(user_f2))
        print('----')
        user_d1 = User.objects.get(username='d1')
        qs = Rede.objects.role_lookups('Diretor', pk='rede').apply_role_lookups(user_d1)
        self.assertEqual(qs.count(), 1)
        print('----')
        user_f4 = User.objects.get(username='f4')
        for user in (user_f1, user_f2, user_d1, user_f4):
            print(user, Produto.objects.all().apply_role_lookups(user))
            print(user, Produto.objects.all().apply_role_lookups(user).has_permission(user))