# Generated by Django 5.0.6 on 2024-07-04 12:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('configuracoes', '0003_alter_contrato_options_alter_jornada_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contrato',
            options={'verbose_name': 'Contrato & Jornada', 'verbose_name_plural': 'Contratos & Jornadas'},
        ),
        migrations.AlterModelOptions(
            name='jornada',
            options={'verbose_name': 'Horas Jornada', 'verbose_name_plural': 'Horas Jornadas'},
        ),
    ]
