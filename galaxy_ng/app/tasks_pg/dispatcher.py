"""
Task dispatcher for PostgreSQL-based task system.
"""
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Type

from django.utils import timezone

from .models import Task, TaskGroup, TaskState, Worker
from .registry import task_registry


logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    Dispatch tasks to the PostgreSQL-based task system.
    """
    
    @staticmethod
    def dispatch(
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        task_group: Optional[TaskGroup] = None,
        immediate: bool = False
    ) -> Task:
        """
        Dispatch a task for execution.
        
        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments  
            task_group: Optional task group
            immediate: Execute immediately in current thread
        
        Returns:
            Task instance
        """
        kwargs = kwargs or {}
        
        # Get function name for task registry
        if hasattr(func, '__name__'):
            func_name = func.__name__
        else:
            func_name = str(func)
        
        # Register function if not already registered
        if func_name not in task_registry:
            task_registry.register(func_name, func)
        
        # Create task
        task = Task.objects.create(
            name=func_name,
            args=list(args),
            kwargs=kwargs,
            task_group=task_group,
            state=TaskState.WAITING
        )
        
        logger.info(f"Dispatched task {task.name} ({task.pulp_id})")
        
        if immediate:
            # Execute immediately in current thread
            TaskExecutor.execute_task(task)
        
        return task
    
    @staticmethod
    def create_task_group(description: str = "") -> TaskGroup:
        """Create a new task group."""
        return TaskGroup.objects.create(description=description)


class TaskExecutor:
    """
    Execute tasks from the PostgreSQL queue.
    """
    
    @staticmethod
    def execute_task(task: Task) -> bool:
        """
        Execute a single task.
        
        Returns:
            True if task completed successfully, False otherwise
        """
        logger.info(f"Executing task {task.name} ({task.pulp_id})")
        
        # Get current worker (create if needed)
        worker = Worker.objects.get_or_create(
            name=f"worker-{threading.current_thread().ident}",
            defaults={'online': True}
        )[0]
        
        # Mark task as running
        task.set_running(worker)
        
        try:
            # Get function from registry
            func = task_registry.get(task.name)
            if not func:
                raise ValueError(f"Task function '{task.name}' not found in registry")
            
            # Execute function
            result = func(*task.args, **task.kwargs)
            
            # Mark as completed
            task.set_completed(result)
            logger.info(f"Task {task.name} completed successfully")
            return True
            
        except Exception as e:
            # Mark as failed
            error_data = {
                'error': str(e),
                'traceback': str(e.__traceback__) if e.__traceback__ else None
            }
            task.set_failed(error_data)
            logger.error(f"Task {task.name} failed: {e}")
            return False
        
        finally:
            # Update worker heartbeat
            worker.heartbeat()


class TaskWorker:
    """
    Task worker process for consuming tasks from PostgreSQL queue.
    """
    
    def __init__(self, worker_name: str, poll_interval: int = 5):
        self.worker_name = worker_name
        self.poll_interval = poll_interval
        self.running = False
        self.worker: Optional[Worker] = None
    
    def start(self):
        """Start the worker."""
        logger.info(f"Starting task worker: {self.worker_name}")
        
        # Register worker
        self.worker, created = Worker.objects.get_or_create(
            name=self.worker_name,
            defaults={'online': True}
        )
        
        if not created:
            self.worker.heartbeat()
        
        self.running = True
        
        try:
            self._run_loop()
        finally:
            self.stop()
    
    def stop(self):
        """Stop the worker."""
        logger.info(f"Stopping task worker: {self.worker_name}")
        self.running = False
        
        if self.worker:
            self.worker.online = False
            self.worker.save(update_fields=['online'])
    
    def _run_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                # Get next task
                task = self._get_next_task()
                
                if task:
                    # Execute task
                    TaskExecutor.execute_task(task)
                else:
                    # No tasks available, wait
                    time.sleep(self.poll_interval)
                
                # Send heartbeat
                if self.worker:
                    self.worker.heartbeat()
                    
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(self.poll_interval)
    
    def _get_next_task(self) -> Optional[Task]:
        """
        Get next available task from queue.
        
        Uses PostgreSQL row locking to prevent race conditions.
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Get next waiting task with row lock
            task = Task.objects.select_for_update(skip_locked=True).filter(
                state=TaskState.WAITING
            ).order_by('pulp_created').first()
            
            if task:
                # Reserve task for this worker
                task.state = TaskState.RUNNING
                task.started_at = timezone.now()
                task.worker = self.worker
                task.save(update_fields=['state', 'started_at', 'worker'])
                
                return task
        
        return None


class TaskScheduler:
    """
    Handle scheduled/recurring tasks.
    """
    
    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self.running = False
    
    def start(self):
        """Start the scheduler."""
        logger.info("Starting task scheduler")
        self.running = True
        
        try:
            self._run_loop()
        finally:
            self.stop()
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping task scheduler")
        self.running = False
    
    def _run_loop(self):
        """Main scheduler loop."""
        from .models import TaskSchedule
        
        while self.running:
            try:
                # Check for due schedules
                due_schedules = TaskSchedule.objects.filter(
                    enabled=True,
                    next_dispatch__lte=timezone.now()
                )
                
                for schedule in due_schedules:
                    try:
                        # Dispatch scheduled task
                        func = task_registry.get(schedule.task_name)
                        if func:
                            task = TaskDispatcher.dispatch(
                                func,
                                args=tuple(schedule.task_args),
                                kwargs=schedule.task_kwargs
                            )
                            
                            # Update schedule
                            schedule.last_task = task
                            schedule.update_next_dispatch()
                            
                            logger.info(f"Dispatched scheduled task: {schedule.name}")
                        else:
                            logger.error(f"Scheduled task function not found: {schedule.task_name}")
                    
                    except Exception as e:
                        logger.error(f"Error dispatching scheduled task {schedule.name}: {e}")
                
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(self.poll_interval)


# Global instances
dispatcher = TaskDispatcher()