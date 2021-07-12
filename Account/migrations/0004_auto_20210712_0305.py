# Generated by Django 3.2.2 on 2021-07-12 02:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Account', '0003_auto_20210712_0256'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='lock_time',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='multiplier',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='trial',
            field=models.SmallIntegerField(default=0),
        ),
    ]