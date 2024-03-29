# Generated by Django 4.1 on 2023-04-02 06:54

from django.db import migrations


def migrate(apps, editor):
    Ano = apps.get_model('investimentos.ano')
    Duvida = apps.get_model('investimentos.duvida')
    Anexo = apps.get_model('investimentos.anexo')
    ano = Ano.objects.get_or_create(ano=2022)[0]
    Duvida.objects.update(ano=ano)
    Anexo.objects.update(ano=ano)


def unmigrate(apps, editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('investimentos', '0009_anexo_ano_duvida_ano'),
    ]

    operations = [
        migrations.RunPython(migrate, unmigrate)
    ]
