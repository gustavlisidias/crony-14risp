# Generated by Django 5.0.6 on 2024-09-10 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0016_alter_tipodocumento_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicofuncionario',
            name='observacoes',
            field=models.TextField(blank=True, null=True, verbose_name='Observações'),
        ),
    ]
