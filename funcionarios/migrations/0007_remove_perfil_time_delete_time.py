# Generated by Django 5.0.6 on 2024-07-10 19:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0006_time_alter_funcionario_email_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='perfil',
            name='time',
        ),
        migrations.DeleteModel(
            name='Time',
        ),
    ]
