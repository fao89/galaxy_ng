"""
Management command to run the task scheduler.
"""
import signal
import sys
from django.core.management.base import BaseCommand

from galaxy_ng.app.tasks_pg.dispatcher import TaskScheduler


class Command(BaseCommand):
    help = 'Run the task scheduler for recurring tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=60,
            help='Polling interval in seconds (default: 60)'
        )

    def handle(self, *args, **options):
        poll_interval = options['poll_interval']

        self.stdout.write(
            self.style.SUCCESS(f'Starting task scheduler (poll interval: {poll_interval}s)')
        )

        # Create and start scheduler
        scheduler = TaskScheduler(poll_interval)
        
        # Handle shutdown signals
        def signal_handler(signum, frame):
            self.stdout.write(
                self.style.WARNING(f'Received signal {signum}, shutting down scheduler...')
            )
            scheduler.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Scheduler interrupted by user')
            )
        finally:
            scheduler.stop()
            self.stdout.write(
                self.style.SUCCESS('Scheduler stopped')
            )