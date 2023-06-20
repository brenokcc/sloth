import os
import requests
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

import graphviz

from sloth.core.valueset import ValueSet, QuerySet


class Command(BaseCommand):

    def handle(self, *args, **options):
        g = graphviz.Digraph('G', filename='/tmp/graph.gv')
        models = [('base', 'servidor')]
        for i, (app_label, model_name) in enumerate(models):
            cls = apps.get_model('convocacao.solicitacaoconvocacao')
            g.edge('/dashboard', f'{app_label}/{model_name}')
            g.edge(f'{app_label}/{model_name}', '{id}'),
            obj = cls.objects.first()
            value_set = obj.view()
            for attr_name in value_set.metadata['names']:
                attr = getattr(obj, attr_name)()
                g.edge('{id}', attr_name)
                if isinstance(attr, ValueSet):
                    for action_name in attr.metadata['actions']:
                        g.edge(attr_name, f'{action_name}')
                if isinstance(attr, QuerySet):
                    add_pk = True
                    for action_name in attr.metadata['global_actions']:
                        g.edge(attr_name, f'{action_name}')
                    for j, action_name in enumerate(attr.metadata['actions']):
                        if add_pk:
                            g.edge(f'{attr_name}', '{id}')
                        g.edge('{id}', action_name)
        g.view()