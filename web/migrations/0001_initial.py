# Generated by Django 5.0.6 on 2024-07-01 20:09

import django.db.models.deletion
import django_ckeditor_5.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('funcionarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Celebracao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=100, verbose_name='Título')),
                ('texto', models.TextField(verbose_name='Celebração')),
                ('data_celebracao', models.DateField(verbose_name='Data da Celebração')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('celebrante', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='funcionario_celebrante', to='funcionarios.funcionario', verbose_name='Celebrante')),
                ('funcionario', models.ManyToManyField(related_name='funcionario_celebracao', to='funcionarios.funcionario', verbose_name='Funcionários')),
            ],
            options={
                'verbose_name': 'Celebração',
                'verbose_name_plural': 'Celebrações',
            },
        ),
        migrations.CreateModel(
            name='Comentario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('comentario', models.TextField(verbose_name='Comentário')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Comentário',
                'verbose_name_plural': 'Comentários',
            },
        ),
        migrations.CreateModel(
            name='Curtida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Curtida',
                'verbose_name_plural': 'Curtidas',
            },
        ),
        migrations.CreateModel(
            name='Humor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('humor', models.CharField(choices=[('5', 'Muito Feliz'), ('4', 'Feliz'), ('3', 'Neutro'), ('2', 'Triste'), ('1', 'Muito Triste')], max_length=1, verbose_name='Humor')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Humor',
                'verbose_name_plural': 'Humores',
            },
        ),
        migrations.CreateModel(
            name='Ouvidoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria', models.IntegerField(choices=[(1, 'Reclamação'), (2, 'Sugestão'), (3, 'Denuncia')], default=1)),
                ('assunto', models.CharField(max_length=255)),
                ('descricao', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Descrição')),
                ('status', models.IntegerField(choices=[(1, 'Aberto'), (2, 'Fechado'), (3, 'Pendente')], default=1)),
                ('anonimo', models.BooleanField(default=True, verbose_name='Anônimo')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ouvidoria_funcionario', to='funcionarios.funcionario')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ouvidoria_responsavel', to='funcionarios.funcionario')),
            ],
            options={
                'verbose_name': 'Ouvidoria',
                'verbose_name_plural': 'Ouvidoria',
            },
        ),
        migrations.CreateModel(
            name='MensagemOuvidoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mensagem', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Mensagem')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('remetente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensagens', to='web.ouvidoria')),
            ],
            options={
                'verbose_name': 'Mensagem Ouvidoria',
                'verbose_name_plural': 'Mensagens Ouvidoria',
            },
        ),
        migrations.CreateModel(
            name='Postagem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=100, verbose_name='Título')),
                ('texto', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Texto')),
                ('slug', models.SlugField(blank=True, default='', editable=False, max_length=120, null=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Postagem',
                'verbose_name_plural': 'Postagens',
            },
        ),
        migrations.CreateModel(
            name='Sugestao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=11, verbose_name='Tipo')),
                ('modelo', models.CharField(max_length=24, verbose_name='Modelo')),
                ('mensagem', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Mensagem')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funcionarios.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Sugestão',
                'verbose_name_plural': 'Sugestões',
            },
        ),
    ]
