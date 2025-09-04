"""
Management command to clean up old tasks and workers.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from galaxy_ng.app.tasks_pg.models import Task, TaskState, Worker


class Command(BaseCommand):
    help = 'Clean up old tasks and mark missing workers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task-retention-days',
            type=int,
            default=30,
            help='Number of days to retain completed/failed tasks (default: 30)'
        )
        parser.add_argument(
            '--worker-timeout-minutes',
            type=int,
            default=5,
            help='Minutes before marking workers as missing (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it'
        )

    def handle(self, *args, **options):
        task_retention_days = options['task_retention_days']
        worker_timeout_minutes = options['worker_timeout_minutes']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Clean up old tasks
        cutoff_date = timezone.now() - timedelta(days=task_retention_days)
        
        old_tasks = Task.objects.filter(
            state__in=TaskState.COMPLETE_STATES,
            finished_at__lt=cutoff_date
        )
        
        task_count = old_tasks.count()
        
        if task_count > 0:
            if not dry_run:
                deleted_count = old_tasks.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted {deleted_count} old tasks')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Would delete {task_count} old tasks')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No old tasks to clean up')
            )

        # Check for missing workers
        if not dry_run:
            Worker.cleanup_missing_workers(worker_timeout_minutes * 60)
            
            missing_workers = Worker.objects.filter(missing=True)
            if missing_workers.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Marked {missing_workers.count()} workers as missing'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All workers are online')
                )
        else:
            timeout_threshold = timezone.now() - timedelta(minutes=worker_timeout_minutes)
            stale_workers = Worker.objects.filter(
                last_heartbeat__lt=timeout_threshold,
                online=True
            )
            
            if stale_workers.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Would mark {stale_workers.count()} workers as missing'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All workers are up to date')
                )

        # Show summary
        total_tasks = Task.objects.count()
        active_workers = Worker.objects.filter(online=True).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Summary: {total_tasks} total tasks, {active_workers} active workers'
            )
        )