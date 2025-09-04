"""
Filesystem-only collection import models without pulpcore dependencies.
"""
from django.db import models
from django.conf import settings


class CollectionImport(models.Model):
    """Model for tracking collection imports in filesystem mode."""
    
    task_id = models.UUIDField(unique=True)
    namespace = models.ForeignKey(
        'Namespace',
        on_delete=models.CASCADE,
        related_name='collection_imports'
    )
    name = models.CharField(max_length=64)
    version = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(
        max_length=50,
        choices=[
            ('waiting', 'Waiting'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='waiting'
    )
    error = models.JSONField(default=dict, blank=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return f"{self.namespace.name}.{self.name}-{self.version}"