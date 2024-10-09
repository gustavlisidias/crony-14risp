# Generated by Django 5.0.6 on 2024-07-01 20:09

import django.db.models.deletion
import django_ckeditor_5.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('configuracoes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CursoFuncionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Curso Funcionário',
                'verbose_name_plural': 'Cursos Funcionário',
            },
        ),
        migrations.CreateModel(
            name='Etapa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=60, verbose_name='Título')),
                ('texto', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Texto')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Etapa',
                'verbose_name_plural': 'Etapas',
            },
        ),
        migrations.CreateModel(
            name='ProgressoEtapa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_conclusao', models.DateTimeField(blank=True, null=True, verbose_name='Data de Conclusão')),
            ],
            options={
                'verbose_name': 'Progresso de Etapa',
                'verbose_name_plural': 'Progresso de Etapas',
            },
        ),
        migrations.CreateModel(
            name='Curso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=60, verbose_name='Título')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('slug', models.SlugField(blank=True, default='', editable=False, max_length=120, null=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('contrato', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='configuracoes.contrato', verbose_name='Contrato')),
            ],
            options={
                'verbose_name': 'Curso',
                'verbose_name_plural': 'Cursos',
            },
        ),
    ]