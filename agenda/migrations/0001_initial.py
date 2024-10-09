# Generated by Django 5.0.6 on 2024-07-01 20:09

import colorfield.fields
import django_ckeditor_5.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Atividade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=256, verbose_name='Título')),
                ('descricao', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Descrição')),
                ('inicio', models.DateTimeField(verbose_name='Início da Atividade')),
                ('final', models.DateTimeField(blank=True, null=True, verbose_name='Final da Atividade')),
                ('data_finalizacao', models.DateTimeField(blank=True, editable=False, null=True, verbose_name='Data de Finalização')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Atividade',
                'verbose_name_plural': 'Atividades',
            },
        ),
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('potencial', models.IntegerField(choices=[(2, 'Alto'), (1, 'Medio'), (0, 'Baixo')], default=1, verbose_name='Potencial')),
                ('desempenho', models.IntegerField(choices=[(2, 'Acima do Esperado'), (1, 'Esperado'), (0, 'Abaixo do Esperado')], default=1, verbose_name='Desempenho')),
                ('observacao', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Observação')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Desempenho',
                'verbose_name_plural': 'Desempenhos',
            },
        ),
        migrations.CreateModel(
            name='DocumentosFerias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('documento', models.BinaryField(verbose_name='Documento')),
                ('caminho', models.CharField(max_length=256, verbose_name='Caminho do Documento')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Documentos de Férias',
                'verbose_name_plural': 'Documento de Férias',
            },
        ),
        migrations.CreateModel(
            name='Ferias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateField(verbose_name='Saída')),
                ('final', models.DateField(verbose_name='Volta')),
                ('abono', models.BooleanField(default=False, verbose_name='Abono Pecuniário')),
                ('decimo', models.BooleanField(default=False, verbose_name='13º Salário')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Férias',
                'verbose_name_plural': 'Férias',
            },
        ),
        migrations.CreateModel(
            name='SolicitacaoFerias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('observacao', models.TextField(verbose_name='Observação')),
                ('inicio', models.DateField(verbose_name='Saída')),
                ('final', models.DateField(verbose_name='Volta')),
                ('abono', models.BooleanField(default=False, verbose_name='Abono Pecuniário')),
                ('decimo', models.BooleanField(default=False, verbose_name='13º Salário')),
                ('status', models.BooleanField(default=False, verbose_name='Aprovado')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
            ],
            options={
                'verbose_name': 'Solicitações de Férias',
                'verbose_name_plural': 'Solicitação de Férias',
            },
        ),
        migrations.CreateModel(
            name='TipoAtividade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=60, verbose_name='Tipo de Atividade')),
                ('slug', models.SlugField(blank=True, default='', editable=False, max_length=120, null=True)),
                ('cor', colorfield.fields.ColorField(default='#FF0000', image_field=None, max_length=25, samples=None)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('avaliativo', models.BooleanField(default=True, verbose_name='Avaliativo')),
            ],
            options={
                'verbose_name': 'Tipo Atividade',
                'verbose_name_plural': 'Tipos Atividade',
            },
        ),
    ]