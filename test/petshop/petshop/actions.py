import json
import time
import datetime
from sloth import actions, meta
from .models import Tratamento, Procedimento, TipoProcedimento, Animal, Doenca
from .tasks import Tarefa


class Teste(actions.Action):

    def view(self):
        # return Tratamento.objects.all()
        # return Tratamento.objects.first().view()
        # return 'static/report.pdf'
        # return 12
        # return dict()
        self.run(Tarefa())
        self.message('Tarefas iniciadas')
        # self.redirect()


class ExibirDataHora(actions.Action):

    class Meta:
        verbose_name = 'Exibir Data/Hora'
        asynchronous = True
        # auto_reload = 5000

    def view(self):
        time.sleep(2)
        return dict(data_hora=datetime.datetime.now())


class FazerAlgumaCoisa(actions.Action):
    x = actions.DateField(label='Data', required=False, initial=datetime.date.today())

    class Meta:
        verbose_name = 'Fazer Alguma Coisa'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info('Ação realizada com sucesso')

    def view(self):
        return self.value_set('get_tipos_procedimentos')

    def submit(self):
        # self.clear()
        # self.message('Ótimo! :)')
        # self.redirect()
        # self.dispose()
        # self.redirect('/app/petshop/animal/')
        # self.reload()
        return self.value_set('get_doencas')
        # self.download('media/animais/a.png')

    def get_tipos_procedimentos(self):
        return self.objects('petshop.tipoprocedimento').all()

    def get_doencas(self):
        return self.objects('petshop.doenca').all()


class FazerAlgumaCoisa2(actions.Action):
    x = actions.DateField(label='Data', required=False, initial='2023-01-01')

    class Meta:
        verbose_name = 'Fazer Alguma Coisa'
        modal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instantiator = Animal.objects.first()

    def get_dados_gerais(self):
        # return self.instantiator.get_dados_gerais()
        return self.instantiator.value_set(
            ('nome', 'tipo'), 'descricao'
        )

    def get_tipos_procedimentos(self):
        return TipoProcedimento.objects.all().actions('edit').preview('get_dados_gerais')#.template('x')

    def view(self):
        self.info('Isso é uma informação!')
        self.alert('Isso é um alerta!')
        return self.value_set('get_dados_gerais')

    def submit(self):
        # self.clear()
        return self.value_set('get_tipos_procedimentos')
        # self.message()
        # self.redirect()


class AlterarContagiosidade(actions.Action):

    class Meta:
        model = Doenca
        fields = 'contagiosa',


class ExibirPermissoes(actions.Action):

    texto = actions.CharField(label='Texto')

    def view(self):
        self.info('Isso é uma informação.')

    def submit(self):
        return self.objects('auth.permission').actions('edit')


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

    def submit(self):
        self.save()
        self.message('Ação realizada com sucesso.')
        self.redirect('.')

    def has_permission(self, user):
        return self.instantiator.data_fim is None


class FinalizarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'data_fim', 'eficaz',
        has_permission = 'Funcionário',
        style = 'success'
        reload = True

    def has_permission(self, user):
        return self.instance.procedimento_set.exists() and self.instance.data_fim is None

class RetomarTratamento(actions.Action):

    class Meta:
        verbose_name = 'Retomar Tratamento'
        style = 'warning'

    def has_permission(self, user):
        return self.instance.data_fim

    def submit(self):
        self.instance.eficaz = None
        self.instance.data_fim = None
        self.instance.save()
        self.message('Tratamento reiniciado com sucesso')
        self.redirect()


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
