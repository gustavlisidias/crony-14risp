# Generated by Django 5.0.6 on 2024-08-02 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0012_remove_funcionario_endereco_funcionario_cep_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='tema',
            field=models.CharField(default='light', editable=False, max_length=10, verbose_name='Tema'),
        ),
    ]