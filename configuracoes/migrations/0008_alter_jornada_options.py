# Generated by Django 5.0.6 on 2024-09-30 18:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('configuracoes', '0007_alter_jornada_ordem_alter_jornada_tipo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='jornada',
            options={'verbose_name': 'Hora Jornada', 'verbose_name_plural': 'Horas Jornadas'},
        ),
    ]
