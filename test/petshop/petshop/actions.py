import json
import time
import datetime
from sloth import actions, meta
from .models import Tratamento, Procedimento, TipoProcedimento, Animal

class ExibirDataHora(actions.Action):

    class Meta:
        verbose_name = 'Exibir Data/Hora'
        asynchronous = True

    def view(self):
        time.sleep(2)
        # self.fade_out()
        # self.auto_reload()
        return dict(data_hora=datetime.datetime.now())


class FazerAlgumaCoisa(actions.Action):
    data = actions.DateField(label='Data', required=False)

    class Meta:
        verbose_name = 'Fazer Alguma Coisa'

    def submit(self):
        # self.clear()
        self.info('Ação realizada com sucesso')
        self.fade_out()
        # self.redirect('/app/petshop/animal/', 'Muito bom!')
        # return self.values('get_tipos_procedimentos')


class FazerAlgumaCoisa2(actions.Action):
    data = actions.DateField(label='Data', required=False)
    class Meta:
        verbose_name = 'Fazer Alguma Coisa'
        modal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(self.instantiator, self.instance, self.instances, 9999)
        self.instantiator = Animal.objects.first()
        self.info('Isso é uma informação!')

    def get_dados_gerais(self):
        # return self.instantiator.get_dados_gerais()
        return self.instantiator.values(
            ('nome', 'tipo'), 'descricao'
        )

    def get_tipos_procedimentos(self):
        return TipoProcedimento.objects.all()

    def view(self):
        return self.values('get_dados_gerais')

    def submit(self):
        self.clear()
        return self.values('get_tipos_procedimentos')
        # self.redirect('..', message='Ação realizada com sucesso!')


class IniciarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'doenca', 'data_inicio'
        related_field = 'animal'
        has_permission = 'Funcionário',


class ExcluirTratamento(actions.Action):

    class Meta:
        style = 'danger'
        confirmation = True
        has_permission = 'Funcionário',

    def submit(self):
        self.instance.delete()
        super().submit()


class ExcluirTratamentos(actions.Action):

    class Meta:
        style = 'danger'
        confirmation = True
        has_permission = 'Funcionário',

    def submit(self):
        for instance in self.instances:
            instance.delete()
        super().submit()


class RegistrarProcedimento(actions.Action):

    class Meta:
        model = Procedimento
        related_field = 'tratamento'
        has_permission = 'Funcionário',
        reload = True
        fieldsets = {
            '': (('tipo', 'data_hora'), 'observacao')
        }

    def has_permission(self, user):
        return self.instantiator.eficaz is None


class FinalizarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'data_fim', 'eficaz',
        has_permission = 'Funcionário',
        style = 'success'
        reload = True

    def has_permission(self, user):
        return self.instance.procedimento_set.exists() and self.instance.eficaz is None


class Batata(actions.Action):

    class Meta:
        style = 'success'

    def has_permission(self, user):
        return True

    def submit(self):
        from pywebpush import webpush
        super(Batata, self).submit()
        webpush(subscription_info=json.loads(self.request.user.push_notification.subscription),
                data="Hello World!",
                vapid_private_key="GoFJpuTAdhepzfxOHdrW7u2ONh7V8ZIjPkjgpWSS3ks",
                vapid_claims={"sub": "mailto:admin@admin.com"})
