# -*- coding: utf-8 -*-
import sys
import json
from datetime import datetime
from django.apps import apps
from django.conf import settings
from oauth2_provider.models import AbstractApplication
from django.contrib.auth.models import User as DjangoUser, AnonymousUser
from sloth.db import models, meta
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives


def user_post_save(instance, created, **kwargs):
    user_role_name = getattr(settings, 'USER_ROLE_NAME', 'Usuário')
    if not instance.roles.contains(user_role_name):
        Role.objects.create(
            user=instance, name=user_role_name, scope_type='auth.user', scope_key='pk', scope_value=instance.pk
        )


models.signals.post_save.connect(user_post_save, sender=DjangoUser)


class UserManager(models.Manager):
    def all(self):
        return self.display(
            'username', 'get_name', 'is_superuser', 'get_roles_names'
        ).actions('login_as_user', 'change_password').verbose_name('Usuários').attach(
            'active', 'inactive'
        ).global_actions('export_csv', 'export_xls', 'print')

    def active(self):
        return self.all().filter(is_active=True).verbose_name('Ativos')

    def inactive(self):
        return self.all().filter(is_active=False).verbose_name('Inativos')


class User(DjangoUser):

    objects = UserManager()

    class Meta:
        proxy = True
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        fieldsets = {
            'Dados Gerais': (('first_name', 'last_name'), 'username', 'email'),
            'Dados de Acesso': (('is_superuser', 'is_staff', 'is_active'),)
        }

    def view(self):
        return self.value_set('get_general_info', 'get_access_info', 'get_roles').actions('print')

    def get_general_info(self):
        return self.value_set(('first_name', 'last_name'), 'username', 'email').verbose_name('Dados Gerais')

    def get_access_info(self):
        return self.value_set('is_superuser',).verbose_name('Dados de Acesso')

    def get_name(self):
        return '{} {}'.format(self.first_name or '', self.last_name or '')

    @meta('Papéis')
    def get_roles(self):
        return self.roles.all().ignore('user').global_actions('print')

    @meta('Papéis')
    def get_roles_names(self):
        return list(self.roles.values_list('name', flat=True).distinct())

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        user_post_save(self, created=created)

class AuthCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )
    secret = models.CharField(max_length=16, verbose_name='Chave')
    active = models.BooleanField(verbose_name='Ativo', default=False)

    class Meta:
        verbose_name = 'Código de Autenticação'
        verbose_name_plural = 'Códigos de Autenticação'

    def __str__(self):
        return self.secret


class RoleManager(models.Manager):

    def all(self):
        return self.display(
            'user', 'name', 'active', 'scope_key', 'get_scope_value'
        ).actions(
            'ActivateUserRole', 'DeactivateUserRole', 'Delete'
        ).limit_per_page(20)

    def active(self):
        return self.filter(active=True)

    def inactive(self):
        return self.filter(active=False)

    def contains(self, *names):
        if 'instance' in self._hints:
            if not hasattr(self._hints['instance'], '_cached_role_names'):
                self._hints['instance']._cached_role_names = self.filter(active=True).values_list('name', flat=True)
            for name in names:
                if name in self._hints['instance']._cached_role_names:
                    return True
            return False
        return self.filter(active=True, name__in=names).exists()

    def names(self):
        return self.values_list('name', flat=True).distinct()


class Role(models.Model):
    user = models.ForeignKey(
        User,
        related_name='roles',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )
    name = models.CharField(max_length=50, verbose_name='Nome')
    scope_key = models.CharField(max_length=50, verbose_name='Escopo', null=True, blank=True)
    scope_type = models.CharField(max_length=50, verbose_name='Tipo do Escopo', null=True, db_index=True, blank=True)
    scope_value = models.IntegerField(verbose_name='Valor do Escopo', null=True, db_index=True, blank=True)
    active = models.BooleanField(verbose_name='Ativo', default=True, blank=True)

    objects = RoleManager()

    class Meta:
        verbose_name = 'Papel'
        verbose_name_plural = 'Papéis'

    def __str__(self):
        if self.scope_key and self.scope_value:
            return '{} - {}'.format(self.name, self.get_scope_value())
        else:
            return '{}'.format(self.name)

    @meta('Referência')
    def get_scope_value(self):
        if self.scope_type:
            return apps.get_model(self.scope_type).objects.filter(pk=self.scope_value).first()


class Scope(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nome')
    description = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Escopo'
        verbose_name_plural = 'Escopos'

    def __str__(self):
        return self.name


class Application(AbstractApplication):
    default_scopes = models.ManyToManyField(Scope, related_name='s2', blank=True)
    available_scopes = models.ManyToManyField(Scope, related_name='s1', blank=True)

    class Meta:
        verbose_name = 'Aplicação'
        verbose_name_plural = 'Aplicações'

    def __str__(self):
        return self.name

    def get_access_tokens(self):
        return self.accesstoken_set.all().verbose_name('Tokens de Acesso')

    def general_data(self):
        return self.value_set('id', 'name').verbose_name('Dados Gerais')

    def access_data(self):
        return self.value_set('client_id', 'client_secret', 'authorization_grant_type').verbose_name('Dados de Acesso')

    def view(self):
        return self.value_set('general_data', 'access_data', 'default_scopes', 'available_scopes')


class TaskManager(models.Manager):
    def all(self):
        return self.lookups(user__username='username').display(
            'id', 'user', 'name', 'start', 'end', 'get_progress', 'message'
        ).attach(
            'running', 'finished', 'unfinished', 'stopped'
        ).global_actions('ManageTaskExecution')

    @meta('Em Execução')
    def running(self):
        return self.all().filter(end__isnull=True, stopped=False).ignore('end')

    @meta('Concluídas com Sucesso')
    def finished(self):
        return self.all().filter(end__isnull=False, stopped=False, error__isnull=True).ignore('end')

    @meta('Concluídas com Erro')
    def unfinished(self):
        return self.all().filter(end__isnull=False, stopped=False, error__isnull=False)

    @meta('Interrompidas pelo Usuário')
    def stopped(self):
        return self.all().filter(end__isnull=False, stopped=True, error__isnull=False)


class Task(models.Model):

    user = models.ForeignKey(User, verbose_name='Usuário', on_delete=models.CASCADE)

    name = models.CharField(verbose_name='Nome', max_length=255)
    start = models.DateTimeField(verbose_name='Início', auto_now=True)
    end = models.DateTimeField(verbose_name='Fim', null=True)

    total = models.IntegerField(verbose_name='Total', default=0)
    partial = models.IntegerField(verbose_name='Parcial', default=0)
    progress = models.IntegerField(verbose_name='Progresso', default=0)
    message = models.CharField(verbose_name='Mensagem', null=True, max_length=255)
    stopped = models.BooleanField(verbose_name='Interrompida', default=False)
    error = models.TextField(verbose_name='Erro', null=True)

    objects = TaskManager()

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def __str__(self):
        return 'Tarefa {}'.format(self.pk)

    def stop(self):
        self.stopped = True
        self.save()

    @meta('Mensagem', 'messages/message')
    def get_message(self):
        if self.error:
            return 'danger', self.error
        elif self.stopped:
            return 'warning', 'Interrompida pelo usuário'
        elif self.progress < 100:
            return 'primary', self.message or 'Em execução'
        else:
            return 'success', self.message or 'Concluída'

    @meta('Progresso', renderer='utils/progress')
    def get_progress(self):
        return self.progress

    @meta('Dados Gerais')
    def get_info(self):
        return self.value_set(('name', 'user'))

    @meta('Processamento')
    def get_process(self):
        return self.value_set(('start', 'end'), ('total', 'partial'), 'get_progress', 'get_message').reload(seconds=5, condition='in_progress', max_requests=360).actions('StopTask')

    def in_progress(self):
        return self.end is None

    def view(self):
        return self.value_set('get_info', 'get_process')

    def has_view_permission(self, user):
        return user.is_superuser or self.user == user


class PushNotification(models.Model):
    user = models.OneToOneField(DjangoUser, verbose_name='Usuário', on_delete=models.CASCADE, related_name='push_notification')
    subscription = models.JSONField(verbose_name='Dados da Inscrição')


class EmailManager(models.Manager):
    def all(self):
        return self.rows().order_by('-id')

    def send(self, to, subject, content, from_email=None, request=None):
        to = [to] if isinstance(to, str) else list(to)
        if request:
            url = '{}://{}'.format(self.request.scheme, self.request.get_host())
            content = content.replace('http://localhost:8000', url)
        email = self.create(from_email=from_email or 'no-reply@mail.com', to=', '.join(to), subject=subject, content=content)
        if settings.DEBUG or 'test' in sys.argv:
            email.debug()


class Email(models.Model):
    from_email = models.EmailField('Remetente')
    to = models.TextField('Destinatário', help_text='Separar endereços de e-mail por ",".')
    subject = models.CharField('Assunto')
    content = models.TextField('Conteúdo', formatted=True)
    sent_at = models.DateTimeField('Data/Hora', null=True)

    objects = EmailManager()

    class Meta:
        icon = 'envelope'
        verbose_name = 'E-mail'
        verbose_name_plural = 'E-mails'
        fieldsets = {
            'Dados Gerais': ('from_email', 'subject', 'to'),
            'Detalhamento': ('content',),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        to = [email.strip() for email in self.to.split(',')]
        msg = EmailMultiAlternatives(self.subject, strip_tags(self.content), self.from_email, to)
        msg.attach_alternative(self.content, "text/html")
        if settings.DEBUG or 'test' in sys.argv or msg.send(fail_silently=True):
            self.sent_at = datetime.now()
        super().save(*args, **kwargs)

    def debug(self):
        l = []
        l.append('-------------- E-MAIL --------------')
        l.append('TO: {}'.format(self.to))
        l.append('SUBJECT: {}'.format(self.subject))
        l.append(self.content)
        l.append('------------------------------------')
        print('\n'.join(l))



setattr(AnonymousUser, 'roles', Role.objects.none())