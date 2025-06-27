from prometheus_client import Counter, Histogram, Gauge
import time
import functools


collection_import_attempts = Counter(
    "galaxy_api_collection_import_attempts",
    "count of collection import attempts"
)

collection_import_failures = Counter(
    "galaxy_api_collection_import_failures",
    "count of collection import failures"
)

collection_import_successes = Counter(
    "galaxy_api_collection_import_successes",
    "count of collections imported successfully"
)

collection_artifact_download_attempts = Counter(
    "galaxy_api_collection_artifact_download_attempts",
    "count of collection artifact download attempts"
)

collection_artifact_download_failures = Counter(
    "galaxy_api_collection_artifact_download_failures",
    "count of collection artifact download failures",
    ["status"]
)

collection_artifact_download_successes = Counter(
    "galaxy_api_collection_artifact_download_successes",
    "count of successful collection artifact downloads"
)

# New performance metrics
api_request_duration = Histogram(
    "galaxy_api_request_duration_seconds",
    "Time spent processing API requests",
    ["method", "endpoint", "status_code"]
)

database_query_duration = Histogram(
    "galaxy_database_query_duration_seconds",
    "Time spent on database queries",
    ["operation", "model"]
)

database_query_count = Counter(
    "galaxy_database_query_total",
    "Total number of database queries",
    ["operation", "model"]
)

cache_operations = Counter(
    "galaxy_cache_operations_total",
    "Total cache operations",
    ["operation", "hit_miss"]
)

cache_operation_duration = Histogram(
    "galaxy_cache_operation_duration_seconds",
    "Time spent on cache operations",
    ["operation"]
)

active_connections = Gauge(
    "galaxy_active_connections",
    "Number of active database connections"
)

namespace_operations = Counter(
    "galaxy_namespace_operations_total",
    "Total namespace operations",
    ["operation", "status"]
)

task_execution_duration = Histogram(
    "galaxy_task_execution_duration_seconds",
    "Time spent executing async tasks",
    ["task_type", "status"]
)

memory_usage = Gauge(
    "galaxy_memory_usage_bytes",
    "Memory usage in bytes",
    ["component"]
)


def track_api_request(method, endpoint):
    """Decorator to track API request metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            try:
                result = func(*args, **kwargs)
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                api_request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)
        return wrapper
    return decorator


def track_database_query(operation, model):
    """Decorator to track database query metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                database_query_duration.labels(
                    operation=operation,
                    model=model
                ).observe(duration)
                database_query_count.labels(
                    operation=operation,
                    model=model
                ).inc()
        return wrapper
    return decorator


def track_cache_operation(operation):
    """Decorator to track cache operation metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            hit_miss = "miss"
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    hit_miss = "hit"
                return result
            finally:
                duration = time.time() - start_time
                cache_operation_duration.labels(
                    operation=operation
                ).observe(duration)
                cache_operations.labels(
                    operation=operation,
                    hit_miss=hit_miss
                ).inc()
        return wrapper
    return decorator


def track_task_execution(task_type):
    """Decorator to track async task execution metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start_time
                task_execution_duration.labels(
                    task_type=task_type,
                    status=status
                ).observe(duration)
        return wrapper
    return decorator
