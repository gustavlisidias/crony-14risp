# Generated by Django 5.0.6 on 2024-08-16 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0014_remove_score_status_score_anomes_score_fechado_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cargo',
            name='slug',
            field=models.SlugField(blank=True, default='', editable=False, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='setor',
            name='slug',
            field=models.SlugField(blank=True, default='', editable=False, max_length=120, null=True),
        ),
    ]
