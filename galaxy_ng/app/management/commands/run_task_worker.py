"""
Management command to run a task worker.
"""
import signal
import sys
from django.core.management.base import BaseCommand
from django.conf import settings

from galaxy_ng.app.tasks_pg.dispatcher import TaskWorker


class Command(BaseCommand):
    help = 'Run a task worker process'

    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-name',
            type=str,
            default=None,
            help='Name for this worker (auto-generated if not provided)'
        )
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=5,
            help='Polling interval in seconds (default: 5)'
        )

    def handle(self, *args, **options):
        worker_name = options['worker_name']
        poll_interval = options['poll_interval']
        
        if not worker_name:
            import socket
            import os
            hostname = socket.gethostname()
            pid = os.getpid()
            worker_name = f"worker-{hostname}-{pid}"

        self.stdout.write(
            self.style.SUCCESS(f'Starting task worker: {worker_name}')
        )

        # Create and start worker
        worker = TaskWorker(worker_name, poll_interval)
        
        # Handle shutdown signals
        def signal_handler(signum, frame):
            self.stdout.write(
                self.style.WARNING(f'Received signal {signum}, shutting down worker...')
            )
            worker.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            worker.start()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Worker interrupted by user')
            )
        finally:
            worker.stop()
            self.stdout.write(
                self.style.SUCCESS('Worker stopped')
            )