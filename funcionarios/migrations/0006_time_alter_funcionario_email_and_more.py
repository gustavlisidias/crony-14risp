# Generated by Django 5.0.6 on 2024-07-10 19:02

import colorfield.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0005_funcionario_conta_banco_funcionario_resp_contato_sec_and_more'),
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
        migrations.AlterField(
            model_name='funcionario',
            name='email',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='estado_civil',
            field=models.CharField(blank=True, choices=[('S', 'Solteiro (a)'), ('C', 'Casado (a)'), ('D', 'Divorciado (a)'), ('V', 'Viúvo (a)'), ('U', 'União Estável')], max_length=1, null=True, verbose_name='Estado Civil'),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='gerente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='funcionarios.funcionario', verbose_name='Responsável'),
        ),
        migrations.AddField(
            model_name='perfil',
            name='time',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='funcionarios.time', verbose_name='Time'),
        ),
    ]
