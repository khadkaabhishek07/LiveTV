from django.db import models
from django.utils.text import slugify


class Channel(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    channel_number = models.PositiveIntegerField()
    logo_url = models.URLField()
    stream_source_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['channel_number', 'name']
        constraints = [
            models.UniqueConstraint(fields=['channel_number', 'name'], name='unique_channel_number_name'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.channel_number} - {self.name}"
