"""
PostgreSQL-based task models.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from django_lifecycle import LifecycleModel


class TaskState:
    """Task state constants."""
    WAITING = "waiting"
    SKIPPED = "skipped"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    CANCELING = "canceling"

    CHOICES = [
        (WAITING, "Waiting"),
        (SKIPPED, "Skipped"),
        (RUNNING, "Running"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELED, "Canceled"),
        (CANCELING, "Canceling"),
    ]

    INCOMPLETE_STATES = [WAITING, RUNNING, CANCELING]
    COMPLETE_STATES = [COMPLETED, FAILED, CANCELED, SKIPPED]


class Task(LifecycleModel):
    """
    PostgreSQL-based task model similar to Pulpcore's Task.
    """
    
    # Task identification
    pulp_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task state and timing
    state = models.CharField(max_length=20, choices=TaskState.CHOICES, default=TaskState.WAITING, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    
    # Timestamps
    pulp_created = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Worker assignment
    worker = models.ForeignKey('Worker', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    # Task details
    args = JSONField(default=list, blank=True)
    kwargs = JSONField(default=dict, blank=True)
    
    # Results and error tracking
    result = JSONField(default=dict, blank=True)
    error = JSONField(default=dict, blank=True)
    
    # Progress tracking
    progress_current = models.IntegerField(default=0)
    progress_total = models.IntegerField(default=100)
    
    # Parent/child task relationships
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_tasks')
    
    # Task group for batching related tasks
    task_group = models.ForeignKey('TaskGroup', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    
    # Reserved resources (for task queuing)
    reserved_resources_record = JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-pulp_created']
        indexes = [
            models.Index(fields=['state', 'pulp_created']),
            models.Index(fields=['worker', 'state']),
            models.Index(fields=['task_group', 'state']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.pulp_id})"
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.progress_total == 0:
            return 0.0
        return (self.progress_current / self.progress_total) * 100
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task duration."""
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    def set_running(self, worker: 'Worker'):
        """Mark task as running."""
        self.state = TaskState.RUNNING
        self.started_at = timezone.now()
        self.worker = worker
        self.save(update_fields=['state', 'started_at', 'worker'])
    
    def set_completed(self, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed."""
        self.state = TaskState.COMPLETED
        self.finished_at = timezone.now()
        self.progress_current = self.progress_total
        if result:
            self.result = result
        self.save(update_fields=['state', 'finished_at', 'progress_current', 'result'])
    
    def set_failed(self, error_data: Dict[str, Any]):
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.finished_at = timezone.now()
        self.error = error_data
        self.save(update_fields=['state', 'finished_at', 'error'])
    
    def update_progress(self, current: int, total: Optional[int] = None):
        """Update task progress."""
        self.progress_current = current
        if total is not None:
            self.progress_total = total
        self.save(update_fields=['progress_current', 'progress_total'])
    
    def cancel(self):
        """Cancel the task."""
        if self.state in TaskState.INCOMPLETE_STATES:
            if self.state == TaskState.RUNNING:
                self.state = TaskState.CANCELING
            else:
                self.state = TaskState.CANCELED
                self.finished_at = timezone.now()
            self.save(update_fields=['state', 'finished_at'])


class TaskGroup(LifecycleModel):
    """
    Group related tasks together.
    """
    
    pulp_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.CharField(max_length=512, blank=True)
    
    # Group tracking
    all_tasks_dispatched = models.BooleanField(default=False)
    
    # Timestamps
    pulp_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-pulp_created']
    
    def __str__(self):
        return f"TaskGroup {self.description} ({self.pulp_id})"
    
    @property 
    def completed_tasks(self) -> int:
        """Count of completed tasks."""
        return self.tasks.filter(state__in=TaskState.COMPLETE_STATES).count()
    
    @property
    def total_tasks(self) -> int:
        """Total number of tasks."""
        return self.tasks.count()
    
    @property
    def is_complete(self) -> bool:
        """Check if all tasks in group are complete."""
        return self.all_tasks_dispatched and self.completed_tasks == self.total_tasks


class CreatedResource(models.Model):
    """
    Track resources created by tasks.
    """
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='created_resources')
    
    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['task', 'created_at']),
        ]
    
    def __str__(self):
        return f"Resource {self.content_type.name}:{self.object_id} (Task: {self.task.pulp_id})"


class Worker(LifecycleModel):
    """
    Task worker process tracking.
    """
    
    name = models.CharField(max_length=255, unique=True)
    
    # Worker state
    online = models.BooleanField(default=True, db_index=True)
    missing = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    last_heartbeat = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Process info
    versions = JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def heartbeat(self):
        """Update worker heartbeat."""
        self.last_heartbeat = timezone.now()
        self.online = True
        self.missing = False
        self.save(update_fields=['last_heartbeat', 'online', 'missing'])
    
    def mark_missing(self):
        """Mark worker as missing."""
        self.missing = True
        self.online = False
        self.save(update_fields=['missing', 'online'])
    
    @classmethod
    def cleanup_missing_workers(cls, heartbeat_timeout_seconds: int = 300):
        """Mark workers as missing if they haven't sent heartbeat."""
        threshold = timezone.now() - timedelta(seconds=heartbeat_timeout_seconds)
        cls.objects.filter(
            last_heartbeat__lt=threshold,
            online=True
        ).update(missing=True, online=False)
    
    @property
    def current_task(self) -> Optional[Task]:
        """Get currently running task."""
        return self.tasks.filter(state=TaskState.RUNNING).first()


class TaskSchedule(models.Model):
    """
    Schedule for recurring tasks.
    """
    
    name = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    
    # Schedule timing
    dispatch_interval = models.DurationField()
    next_dispatch = models.DateTimeField(db_index=True)
    last_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Task configuration
    task_args = JSONField(default=list, blank=True)
    task_kwargs = JSONField(default=dict, blank=True)
    
    # Control flags
    enabled = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['next_dispatch']
    
    def __str__(self):
        return f"Schedule: {self.name}"
    
    def should_dispatch(self) -> bool:
        """Check if task should be dispatched."""
        return self.enabled and timezone.now() >= self.next_dispatch
    
    def update_next_dispatch(self):
        """Update next dispatch time."""
        self.next_dispatch = timezone.now() + self.dispatch_interval
        self.save(update_fields=['next_dispatch'])