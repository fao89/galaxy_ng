"""
Filesystem-only config models.
"""
from django.db import models


class Setting(models.Model):
    """Model for storing dynamic configuration settings."""
    
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"