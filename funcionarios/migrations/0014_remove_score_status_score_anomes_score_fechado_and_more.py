# Generated by Django 5.0.6 on 2024-08-08 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0013_perfil_tema'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='score',
            name='status',
        ),
        migrations.AddField(
            model_name='score',
            name='anomes',
            field=models.PositiveIntegerField(default=202408, editable=False, verbose_name='Referência Ano Mês'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='score',
            name='fechado',
            field=models.BooleanField(default=False, verbose_name='Fechado'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='modelo',
            field=models.CharField(choices=[('PCC', 'Parar / Continuar / Começar'), ('SCI', 'Situação, Comportamento ou Impacto'), ('CNV', 'Comunicação Não Violenta'), ('GRL', 'Geral')], max_length=100),
        ),
        migrations.AlterField(
            model_name='score',
            name='data_cadastro',
            field=models.DateTimeField(auto_now=True, verbose_name='Data de Cadastro'),
        ),
        migrations.AlterField(
            model_name='score',
            name='pontuacao',
            field=models.FloatField(default=5, verbose_name='Pontuação'),
        ),
    ]
