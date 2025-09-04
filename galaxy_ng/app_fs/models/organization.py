"""
Filesystem-only organization models without pulpcore dependencies.
"""
from django.db import models
from django.conf import settings


class Organization(models.Model):
    """Filesystem-based organization model."""
    
    name = models.CharField(max_length=512, unique=True)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return self.name


class Team(models.Model):
    """Filesystem-based team model."""
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='teams'
    )
    name = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('organization', 'name')
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"