# Generated by Django 5.0.6 on 2024-07-04 12:30

import colorfield.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0002_remove_perfil_time_delete_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='Time',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=60, verbose_name='Título')),
                ('cor', colorfield.fields.ColorField(default='#FFFFFF', image_field=None, max_length=25, samples=None)),
                ('icone', models.CharField(default='<i class="fa-duotone fa-medal"></i>', max_length=60, verbose_name='Ícone')),
            ],
            options={
                'verbose_name': 'Time',
                'verbose_name_plural': 'Times',
            },
        ),
        migrations.RenameField(
            model_name='funcionario',
            old_name='expedicao',
            new_name='data_expedicao',
        ),
        migrations.RemoveField(
            model_name='funcionario',
            name='ip',
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='nome_mae',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Nome da Mãe'),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='nome_pai',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Nome do Pai'),
        ),
        migrations.AddField(
            model_name='perfil',
            name='time',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='funcionarios.time', verbose_name='Time'),
        ),
    ]