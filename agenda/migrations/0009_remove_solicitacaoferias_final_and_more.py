# Generated by Django 5.0.6 on 2024-10-15 12:57

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0008_remove_ferias_entrada_remove_ferias_retorno_and_more'),
        ('funcionarios', '0021_jornadafuncionario_final_vigencia_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='solicitacaoferias',
            name='final',
        ),
        migrations.RemoveField(
            model_name='solicitacaoferias',
            name='inicio',
        ),
        migrations.AddField(
            model_name='atividade',
            name='solic_ferias',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to='agenda.solicitacaoferias'),
        ),
        migrations.AddField(
            model_name='solicitacaoferias',
            name='final_ferias',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Final Férias'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='solicitacaoferias',
            name='final_periodo',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Final Período'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='solicitacaoferias',
            name='inicio_ferias',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Início Férias'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='solicitacaoferias',
            name='inicio_periodo',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Início Período'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='atividade',
            name='autor',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='autor_atividade', to='funcionarios.funcionario'),
        ),
    ]
