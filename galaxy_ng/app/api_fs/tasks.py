"""
Task API endpoints for PostgreSQL-based task system.
"""
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from galaxy_ng.app.tasks_pg.models import Task, TaskGroup, Worker
from galaxy_ng.app.tasks_pg.dispatcher import dispatcher


class TaskViewSet(viewsets.ViewSet):
    """API endpoints for task management."""
    
    def list(self, request):
        """List tasks."""
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        state = request.query_params.get('state')
        
        queryset = Task.objects.all()
        
        if state:
            queryset = queryset.filter(state=state)
        
        # Get total count
        total = queryset.count()
        
        # Apply pagination
        tasks = queryset[offset:offset + limit]
        
        # Format response
        results = []
        for task in tasks:
            results.append(self._format_task_response(task))
        
        return Response({
            "meta": {"count": total},
            "data": results
        })
    
    def retrieve(self, request, pk=None):
        """Get specific task."""
        try:
            task = Task.objects.get(pulp_id=pk)
            return Response(self._format_task_response(task))
        except Task.DoesNotExist:
            raise Http404()
    
    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        """Cancel a task."""
        try:
            task = Task.objects.get(pulp_id=pk)
            task.cancel()
            return Response(self._format_task_response(task))
        except Task.DoesNotExist:
            raise Http404()
    
    def _format_task_response(self, task: Task) -> dict:
        """Format task for API response."""
        return {
            "pulp_id": str(task.pulp_id),
            "pulp_created": task.pulp_created.isoformat(),
            "pulp_href": f"/pulp/api/v3/tasks/{task.pulp_id}/",
            "state": task.state,
            "name": task.name,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "error": task.error if task.error else None,
            "worker": task.worker.name if task.worker else None,
            "parent_task": str(task.parent_task.pulp_id) if task.parent_task else None,
            "child_tasks": [str(child.pulp_id) for child in task.child_tasks.all()],
            "task_group": str(task.task_group.pulp_id) if task.task_group else None,
            "progress_reports": [
                {
                    "message": task.name,
                    "code": "sync",
                    "state": task.state,
                    "total": task.progress_total,
                    "done": task.progress_current,
                    "suffix": ""
                }
            ],
            "created_resources": [
                {
                    "pulp_href": f"/pulp/api/v3/{resource.content_type.model}/{resource.object_id}/",
                    "pulp_id": resource.object_id
                }
                for resource in task.created_resources.all()
            ],
            "reserved_resources_record": task.reserved_resources_record
        }


class TaskGroupViewSet(viewsets.ViewSet):
    """API endpoints for task group management."""
    
    def list(self, request):
        """List task groups."""
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Get total count and apply pagination
        total = TaskGroup.objects.count()
        task_groups = TaskGroup.objects.all()[offset:offset + limit]
        
        # Format response
        results = []
        for group in task_groups:
            results.append(self._format_group_response(group))
        
        return Response({
            "meta": {"count": total},
            "data": results
        })
    
    def retrieve(self, request, pk=None):
        """Get specific task group."""
        try:
            group = TaskGroup.objects.get(pulp_id=pk)
            return Response(self._format_group_response(group))
        except TaskGroup.DoesNotExist:
            raise Http404()
    
    def _format_group_response(self, group: TaskGroup) -> dict:
        """Format task group for API response."""
        return {
            "pulp_id": str(group.pulp_id),
            "description": group.description,
            "all_tasks_dispatched": group.all_tasks_dispatched,
            "waiting": group.tasks.filter(state="waiting").count(),
            "skipped": group.tasks.filter(state="skipped").count(),
            "running": group.tasks.filter(state="running").count(),
            "completed": group.tasks.filter(state="completed").count(),
            "failed": group.tasks.filter(state="failed").count(),
            "canceled": group.tasks.filter(state="canceled").count(),
            "canceling": group.tasks.filter(state="canceling").count(),
            "group_progress_reports": [],
            "tasks": [
                {
                    "pulp_href": f"/pulp/api/v3/tasks/{task.pulp_id}/",
                    "pulp_id": str(task.pulp_id),
                    "state": task.state
                }
                for task in group.tasks.all()
            ]
        }


class WorkerViewSet(viewsets.ViewSet):
    """API endpoints for worker management."""
    
    def list(self, request):
        """List workers."""
        online_only = request.query_params.get('online', 'false').lower() == 'true'
        
        queryset = Worker.objects.all()
        if online_only:
            queryset = queryset.filter(online=True)
        
        workers = list(queryset)
        
        # Format response
        results = []
        for worker in workers:
            results.append(self._format_worker_response(worker))
        
        return Response({
            "meta": {"count": len(results)},
            "data": results
        })
    
    def retrieve(self, request, pk=None):
        """Get specific worker."""
        try:
            worker = Worker.objects.get(name=pk)
            return Response(self._format_worker_response(worker))
        except Worker.DoesNotExist:
            raise Http404()
    
    def _format_worker_response(self, worker: Worker) -> dict:
        """Format worker for API response."""
        current_task = worker.current_task
        
        return {
            "pulp_id": worker.name,
            "name": worker.name,
            "last_heartbeat": worker.last_heartbeat.isoformat(),
            "online": worker.online,
            "missing": worker.missing,
            "versions": worker.versions,
            "current_task": {
                "pulp_href": f"/pulp/api/v3/tasks/{current_task.pulp_id}/",
                "pulp_id": str(current_task.pulp_id),
                "state": current_task.state
            } if current_task else None
        }