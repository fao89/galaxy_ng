"""Utility functions for AH tests."""
import logging
import time
from typing import Optional, Dict, Any

from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_POLLING
from .urls import url_safe_join
from .errors import (
    TaskWaitingTimeout
)

logger = logging.getLogger(__name__)


def wait_for_all_tasks(client, timeout=300):
    ready = False
    wait_until = time.time() + timeout

    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = client(
            "pulp/api/v3/tasks/?state=running",
        )["count"]

        waiting_count = client(
            "pulp/api/v3/tasks/?state=waiting",
        )["count"]

        ready = running_count == 0 and waiting_count == 0

        time.sleep(SLEEP_SECONDS_POLLING)


def wait_for_all_tasks_gk(gc, timeout=300):
    ready = False
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = gc.get("pulp/api/v3/tasks/?state=running")["count"]
        waiting_count = gc.get("pulp/api/v3/tasks/?state=waiting")["count"]
        ready = running_count == 0 and waiting_count == 0
        time.sleep(SLEEP_SECONDS_POLLING)


def wait_for_task_completion(
    task_api,
    task_id: str,
    timeout: int = 30,
    poll_interval: float = 0.1,
    max_poll_interval: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    Optimized task waiting with exponential backoff and shorter initial intervals.

    Args:
        task_api: API client for task operations
        task_id: Task ID to wait for
        timeout: Maximum time to wait in seconds
        poll_interval: Initial polling interval in seconds
        max_poll_interval: Maximum polling interval in seconds

    Returns:
        Task data if completed, None if timeout
    """
    start_time = time.time()
    current_interval = poll_interval

    while time.time() - start_time < timeout:
        try:
            task = task_api.get(task_id)
            if task.get('state') in ['completed', 'failed', 'canceled']:
                logger.debug(f"Task {task_id} completed in {time.time() - start_time:.2f}s")
                return task
        except Exception as e:
            logger.warning(f"Error checking task {task_id}: {e}")

        # Exponential backoff with maximum interval
        time.sleep(current_interval)
        current_interval = min(current_interval * 1.5, max_poll_interval)

    logger.warning(f"Task {task_id} timeout after {timeout}s")
    return None


def wait_for_task(gc, task_resp):
    """Optimized task waiting with reduced sleep times"""
    task_id = task_resp['task'].split('/')[-2]

    # Use optimized waiting with much shorter initial intervals
    start_time = time.time()
    poll_interval = 0.1  # Start with 100ms
    max_interval = 1.0   # Max 1 second
    timeout = 30

    while time.time() - start_time < timeout:
        try:
            task = gc.get(task_resp['task'])
            if task['state'] in ['completed', 'failed', 'canceled']:
                return task
        except Exception as e:
            logger.warning(f"Error waiting for task: {e}")

        time.sleep(poll_interval)
        # Gradually increase interval but cap at max_interval
        poll_interval = min(poll_interval * 1.2, max_interval)

    logger.error(f"Task timeout after {timeout}s")
    return None


def wait_for_task_ui_client(client, task_url):
    """Optimized UI client task waiting"""
    start_time = time.time()
    poll_interval = 0.1
    max_interval = 1.0
    timeout = 30

    while time.time() - start_time < timeout:
        try:
            task_resp = client.get(task_url)
            if task_resp['state'] in ['completed', 'failed', 'canceled']:
                return task_resp
        except Exception as e:
            logger.warning(f"Error waiting for UI task: {e}")

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.2, max_interval)

    logger.error(f"UI task timeout after {timeout}s")
    return None


def wait_for_namespace_tasks_gk(gc, timeout=300):
    ready = False
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = gc.get("pulp/api/v3/tasks/?state=running&name__contains=namespace")["count"]
        waiting_count = gc.get("pulp/api/v3/tasks/?state=waiting&name__contains=namespace")["count"]
        ready = running_count == 0 and waiting_count == 0
        time.sleep(SLEEP_SECONDS_POLLING)


def wait_for_multiple_tasks(gc, task_list, timeout=60):
    """
    Optimized waiting for multiple tasks with parallel checking.

    Args:
        gc: Galaxy client
        task_list: List of task responses
        timeout: Maximum time to wait for all tasks

    Returns:
        List of completed tasks
    """
    start_time = time.time()
    completed_tasks = []
    remaining_tasks = task_list.copy()
    poll_interval = 0.1
    max_interval = 1.0

    while remaining_tasks and time.time() - start_time < timeout:
        # Check all remaining tasks in parallel
        tasks_to_remove = []

        for task_resp in remaining_tasks:
            try:
                task = gc.get(task_resp['task'])
                if task['state'] in ['completed', 'failed', 'canceled']:
                    completed_tasks.append(task)
                    tasks_to_remove.append(task_resp)
            except Exception as e:
                logger.warning(f"Error checking task: {e}")

        # Remove completed tasks
        for task_resp in tasks_to_remove:
            remaining_tasks.remove(task_resp)

        if remaining_tasks:
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.2, max_interval)

    if remaining_tasks:
        logger.warning(f"{len(remaining_tasks)} tasks did not complete within {timeout}s")

    return completed_tasks


def wait_for_import_task_complete(gc, task_url, timeout=30):
    """Optimized import task waiting"""
    return wait_for_task_completion(gc, task_url, timeout=timeout)


def wait_for_url(gc, url, timeout=30):
    """Optimized URL availability waiting"""
    start_time = time.time()
    poll_interval = 0.1
    max_interval = 1.0

    while time.time() - start_time < timeout:
        try:
            resp = gc.get(url)
            if resp:
                return resp
        except Exception as e:
            logger.debug(f"URL {url} not ready: {e}")

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.2, max_interval)

    logger.error(f"URL {url} not available after {timeout}s")
    return None


class TaskFailed(Exception):
    def __init__(self, message):
        self.message = message
