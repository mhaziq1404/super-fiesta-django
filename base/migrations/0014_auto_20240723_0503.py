# Generated by Django 3.2.7 on 2024-07-23 05:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0013_auto_20240723_0421'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='room',
            name='opponent_user',
        ),
        migrations.AddField(
            model_name='room',
            name='is_2player',
            field=models.BooleanField(default=False),
        ),
    ]
