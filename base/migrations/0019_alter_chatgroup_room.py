# Generated by Django 3.2.25 on 2024-08-01 07:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0018_chatgroup_room'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatgroup',
            name='room',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.room'),
        ),
    ]
