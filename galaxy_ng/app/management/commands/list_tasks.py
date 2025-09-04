"""
Management command to list and monitor tasks.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from galaxy_ng.app.tasks_pg.models import Task, TaskState, Worker


class Command(BaseCommand):
    help = 'List and monitor tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--state',
            type=str,
            choices=[choice[0] for choice in TaskState.CHOICES],
            help='Filter by task state'
        )
        parser.add_argument(
            '--worker',
            type=str,
            help='Filter by worker name'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Limit number of results (default: 20)'
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch for task changes (refresh every 5 seconds)'
        )
        parser.add_argument(
            '--show-workers',
            action='store_true',
            help='Show worker status instead of tasks'
        )

    def handle(self, *args, **options):
        if options['watch']:
            self._watch_tasks(options)
        elif options['show_workers']:
            self._show_workers()
        else:
            self._list_tasks(options)

    def _list_tasks(self, options):
        """List tasks with filters."""
        queryset = Task.objects.all()
        
        if options['state']:
            queryset = queryset.filter(state=options['state'])
        
        if options['worker']:
            queryset = queryset.filter(worker__name=options['worker'])
        
        tasks = queryset.order_by('-pulp_created')[:options['limit']]
        
        if not tasks:
            self.stdout.write(self.style.WARNING('No tasks found'))
            return
        
        # Header
        self.stdout.write(
            f"{'ID':<8} {'State':<12} {'Name':<30} {'Worker':<20} {'Created':<20}"
        )
        self.stdout.write('-' * 90)
        
        # Tasks
        for task in tasks:
            worker_name = task.worker.name if task.worker else 'None'
            created = task.pulp_created.strftime('%Y-%m-%d %H:%M:%S')
            
            # Color code by state
            if task.state == TaskState.COMPLETED:
                style = self.style.SUCCESS
            elif task.state == TaskState.FAILED:
                style = self.style.ERROR
            elif task.state == TaskState.RUNNING:
                style = self.style.WARNING
            else:
                style = self.style.HTTP_INFO
            
            line = f"{str(task.pulp_id)[:8]:<8} {task.state:<12} {task.name[:30]:<30} {worker_name[:20]:<20} {created:<20}"
            self.stdout.write(style(line))

    def _show_workers(self):
        """Show worker status."""
        workers = Worker.objects.all().order_by('name')
        
        if not workers:
            self.stdout.write(self.style.WARNING('No workers found'))
            return
        
        # Header
        self.stdout.write(
            f"{'Name':<30} {'Status':<10} {'Last Heartbeat':<20} {'Current Task':<15}"
        )
        self.stdout.write('-' * 75)
        
        # Workers
        for worker in workers:
            if worker.online:
                status = self.style.SUCCESS('Online')
            elif worker.missing:
                status = self.style.ERROR('Missing')
            else:
                status = self.style.WARNING('Offline')
            
            heartbeat = worker.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S')
            current_task = str(worker.current_task.pulp_id)[:15] if worker.current_task else 'None'
            
            line = f"{worker.name[:30]:<30} {worker.online and 'Online' or (worker.missing and 'Missing' or 'Offline'):<10} {heartbeat:<20} {current_task:<15}"
            self.stdout.write(status(line))

    def _watch_tasks(self, options):
        """Watch tasks with auto-refresh."""
        import time
        import os
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Show timestamp
                now = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                self.stdout.write(
                    self.style.SUCCESS(f'Task Monitor - {now} (Press Ctrl+C to exit)')
                )
                self.stdout.write('')
                
                # Show task counts by state
                self._show_task_summary()
                self.stdout.write('')
                
                # Show recent tasks
                self.stdout.write(self.style.HTTP_INFO('Recent Tasks:'))
                self._list_tasks(options)
                
                # Wait before refresh
                time.sleep(5)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nMonitoring stopped'))

    def _show_task_summary(self):
        """Show task count summary."""
        from django.db.models import Count
        
        summary = Task.objects.values('state').annotate(count=Count('state'))
        
        counts = {item['state']: item['count'] for item in summary}
        
        total = sum(counts.values())
        
        self.stdout.write(f"Total Tasks: {total}")
        for state in TaskState.CHOICES:
            state_name = state[0]
            count = counts.get(state_name, 0)
            if count > 0:
                if state_name in [TaskState.COMPLETED]:
                    style = self.style.SUCCESS
                elif state_name in [TaskState.FAILED]:
                    style = self.style.ERROR
                elif state_name in [TaskState.RUNNING]:
                    style = self.style.WARNING
                else:
                    style = self.style.HTTP_INFO
                
                self.stdout.write(style(f"  {state[1]}: {count}"))