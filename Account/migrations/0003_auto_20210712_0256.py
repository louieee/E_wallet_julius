# Generated by Django 3.2.2 on 2021-07-12 01:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Account', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(default='', max_length=50)),
                ('data', models.TextField(default='{}')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('expiry_date', models.DateTimeField()),
            ],
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
