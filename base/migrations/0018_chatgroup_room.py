# Generated by Django 3.2.25 on 2024-07-29 05:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0017_auto_20240726_0710'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatgroup',
            name='room',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.room'),
        ),
    ]
