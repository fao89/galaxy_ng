"""
Filesystem-only namespace models without pulpcore dependencies.
"""
from django.db import models
from django.conf import settings


class Namespace(models.Model):
    """Filesystem-based namespace model."""
    
    name = models.CharField(max_length=64, unique=True)
    company = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    location = models.CharField(max_length=256, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return self.name
        
    @property
    def metadata(self):
        """Return namespace metadata."""
        return {
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'location': self.location,
        }


class NamespaceLink(models.Model):
    """Links associated with a namespace."""
    
    namespace = models.ForeignKey(
        Namespace, 
        on_delete=models.CASCADE,
        related_name='links'
    )
    name = models.CharField(max_length=256)
    url = models.URLField()
    
    class Meta:
        unique_together = ('namespace', 'name')
    
    def __str__(self):
        return f"{self.namespace.name} - {self.name}"