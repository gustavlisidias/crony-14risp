# Generated by Django 5.0.6 on 2024-07-22 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0007_remove_perfil_time_delete_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='jornadafuncionario',
            name='ordem',
            field=models.IntegerField(default=1, verbose_name='Ordem'),
            preserve_default=False,
        ),
    ]
