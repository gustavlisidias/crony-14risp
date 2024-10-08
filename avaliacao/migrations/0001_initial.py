# Generated by Django 5.0.6 on 2024-10-01 13:15

import django.db.models.deletion
import django_ckeditor_5.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('funcionarios', '0020_alter_funcionario_conta_banco'),
    ]

    operations = [
        migrations.CreateModel(
            name='Criterio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, verbose_name='Nome')),
                ('slug', models.SlugField(blank=True, default='', editable=False, max_length=240, null=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Critério',
                'verbose_name_plural': 'Critérios',
            },
        ),
        migrations.CreateModel(
            name='Pergunta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=120, verbose_name='Título')),
                ('texto', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Texto')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Pergunta',
                'verbose_name_plural': 'Perguntas',
            },
        ),
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=120, verbose_name='Título')),
                ('descricao', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Descrição')),
                ('inicio', models.DateField(verbose_name='Início')),
                ('final', models.DateField(verbose_name='Final')),
                ('status', models.BooleanField(default=False, verbose_name='Fechado')),
                ('slug', models.SlugField(blank=True, default='', editable=False, max_length=240, null=True)),
                ('data_encerramento', models.DateField(verbose_name='Data de Encerramento')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('avaliado', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='avaliado_avaliacao', to='funcionarios.funcionario', verbose_name='Avaliado')),
                ('avaliadores', models.ManyToManyField(related_name='avaliadores_avaliacao', to='funcionarios.funcionario', verbose_name='Avaliadores')),
            ],
            options={
                'verbose_name': 'Avaliação',
                'verbose_name_plural': 'Avaliações',
            },
        ),
        migrations.CreateModel(
            name='PesoAvaliador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nivel', models.IntegerField(choices=[(2, 'Gestor'), (1, 'Par'), (0, 'Auto')], verbose_name='Nível')),
                ('peso', models.FloatField(verbose_name='Peso')),
                ('avaliacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='avaliacao.avaliacao', verbose_name='Avaliação')),
            ],
            options={
                'verbose_name': 'Nível por Avaliação',
                'verbose_name_plural': 'Níveis por Avaliação',
            },
        ),
        migrations.CreateModel(
            name='PesoCriterio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('peso', models.FloatField(verbose_name='Peso')),
                ('avaliacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='avaliacao.avaliacao', verbose_name='Avaliação')),
                ('criterio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='avaliacao.criterio', verbose_name='Critério')),
                ('pergunta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='avaliacao.pergunta', verbose_name='Pergunta')),
            ],
            options={
                'verbose_name': 'Pergunta por Avaliação',
                'verbose_name_plural': 'Perguntas por Avaliação',
            },
        ),
        migrations.CreateModel(
            name='Resposta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota', models.FloatField(verbose_name='Nota')),
                ('observacao', models.TextField(verbose_name='Observação')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funcionario_reposta_avaliacao', to='funcionarios.funcionario', verbose_name='Funcionário')),
                ('pergunta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='avaliacao.pesocriterio', verbose_name='Pergunta')),
            ],
            options={
                'verbose_name': 'Resposta',
                'verbose_name_plural': 'Respostas',
            },
        ),
    ]
