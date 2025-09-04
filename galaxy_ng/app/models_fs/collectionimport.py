"""
Filesystem-based collection import model replacement.
"""
from django.db import models
from django.urls import reverse
from django_lifecycle import LifecycleModel

from galaxy_ng.app.tasks_fs.base import task_manager
from .namespace import Namespace

__all__ = (
    "CollectionImport",
)


class CollectionImport(LifecycleModel):
    """
    Filesystem-backed collection import tracking.
    
    Replaces Pulp task references with simple task tracking.
    """
    
    # Use UUID for task ID instead of Pulp task reference
    task_id = models.UUIDField(primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, editable=False)
    version = models.CharField(max_length=32, editable=False)
    
    # Additional tracking fields
    status = models.CharField(max_length=20, default='pending')  # pending, running, success, failure
    username = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def task(self):
        """Get task details from task manager."""
        return task_manager.get_task(str(self.task_id))
    
    @property
    def state(self):
        """Get task state."""
        task = self.task
        return task.state.value if task else self.status
    
    @property
    def messages(self):
        """Get task messages/errors."""
        task = self.task
        if task and task.error:
            return [{"message": task.error, "level": "error"}]
        elif self.error_message:
            return [{"message": self.error_message, "level": "error"}]
        return []
    
    def get_absolute_url(self):
        return reverse('galaxy:api:content:collection-import', args=[str(self.task_id)])
    
    def update_from_task(self):
        """Update model from task manager state."""
        task = self.task
        if task:
            self.status = task.state.value
            if task.error:
                self.error_message = task.error
            self.save(update_fields=['status', 'error_message'])
    
    @classmethod
    def create_for_task(cls, task_id: str, namespace: str, name: str, version: str, username: str = '') -> 'CollectionImport':
        """Create CollectionImport for a task."""
        import uuid
        
        # Get or create namespace
        namespace_obj, _ = Namespace.objects.get_or_create(name=namespace)
        
        return cls.objects.create(
            task_id=uuid.UUID(task_id),
            namespace=namespace_obj,
            name=name,
            version=version,
            username=username
        )