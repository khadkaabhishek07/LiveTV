from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('channel_number', models.PositiveIntegerField()),
                ('logo_url', models.URLField()),
                ('stream_source_url', models.URLField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['channel_number', 'name']},
        ),
        migrations.AddConstraint(
            model_name='channel',
            constraint=models.UniqueConstraint(fields=('channel_number', 'name'), name='unique_channel_number_name'),
        ),
    ]
