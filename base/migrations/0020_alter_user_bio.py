# Generated by Django 3.2.25 on 2024-08-02 02:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0019_alter_chatgroup_room'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='bio',
            field=models.TextField(default='The User to lazy to add a Bio', null=True),
        ),
    ]
