"""
Centralized caching utilities for Galaxy NG performance optimization.

This module provides caching decorators, cache management utilities,
and performance-optimized caching strategies.
"""

import hashlib
import json
import logging
import time
from functools import wraps
from typing import Any, Optional, Callable, Dict, List

from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

logger = logging.getLogger(__name__)


# Cache configuration constants
DEFAULT_CACHE_TIMEOUT = 300  # 5 minutes
LONG_CACHE_TIMEOUT = 3600   # 1 hour
SHORT_CACHE_TIMEOUT = 60    # 1 minute

# Cache key prefixes
NAMESPACE_CACHE_PREFIX = "galaxy:namespace:"
COLLECTION_CACHE_PREFIX = "galaxy:collection:"
USER_CACHE_PREFIX = "galaxy:user:"
TASK_CACHE_PREFIX = "galaxy:task:"


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from arguments.

    Args:
        prefix: Cache key prefix
        *args: Arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Generated cache key
    """
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {},
        'timestamp': int(time.time() / 60)  # Cache for 1 minute intervals
    }

    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()

    return f"{prefix}{key_hash}"


def cached_method(timeout: int = DEFAULT_CACHE_TIMEOUT, key_prefix: str = "method"):
    """
    Decorator for caching method results.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key based on method name, instance, and arguments
            cache_key = generate_cache_key(
                f"{key_prefix}:{func.__name__}:",
                getattr(self, 'pk', id(self)),
                *args,
                **kwargs
            )

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # Execute function and cache result
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache miss for {cache_key}, cached result")

            return result
        return wrapper
    return decorator


def cached_queryset(timeout: int = DEFAULT_CACHE_TIMEOUT, key_prefix: str = "queryset"):
    """
    Decorator for caching QuerySet results.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(
                f"{key_prefix}:{func.__name__}:",
                *args,
                **kwargs
            )

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"QuerySet cache hit for {cache_key}")
                return cached_result

            result = func(*args, **kwargs)

            # Convert QuerySet to list for caching
            if isinstance(result, QuerySet):
                cached_data = list(result)
            else:
                cached_data = result

            cache.set(cache_key, cached_data, timeout)
            logger.debug(f"QuerySet cache miss for {cache_key}, cached result")

            return result
        return wrapper
    return decorator


class CacheManager:
    """Centralized cache management utilities."""

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """
        Invalidate cache keys matching a pattern.

        Args:
            pattern: Pattern to match cache keys

        Returns:
            Number of keys invalidated
        """
        # This is a simplified implementation
        # In production, consider using Redis pattern matching
        try:
            cache.delete_many([pattern])
            return 1
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

    @staticmethod
    def warm_cache(cache_funcs: List[Callable]) -> None:
        """
        Warm up cache by pre-executing cache functions.

        Args:
            cache_funcs: List of functions to execute for cache warming
        """
        for func in cache_funcs:
            try:
                func()
                logger.debug(f"Cache warmed for {func.__name__}")
            except Exception as e:
                logger.error(f"Error warming cache for {func.__name__}: {e}")

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        # This would need to be implemented based on cache backend
        return {
            'backend': settings.CACHES.get('default', {}).get('BACKEND', 'unknown'),
            'timestamp': time.time()
        }


# Namespace-specific cache utilities
class NamespaceCache:
    """Cache utilities specific to namespace operations."""

    @staticmethod
    @cached_method(timeout=LONG_CACHE_TIMEOUT, key_prefix=NAMESPACE_CACHE_PREFIX)
    def get_namespace_owners(namespace_id: int) -> List[str]:
        """
        Cached namespace owners lookup.

        Args:
            namespace_id: Namespace ID

        Returns:
            List of owner usernames
        """
        from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
        from galaxy_ng.app.models import Namespace

        try:
            namespace = Namespace.objects.get(id=namespace_id)
            owners = get_v3_namespace_owners(namespace)
            return [owner.username for owner in owners]
        except Exception as e:
            logger.error(f"Error getting namespace owners for {namespace_id}: {e}")
            return []

    @staticmethod
    def invalidate_namespace_cache(namespace_id: int) -> None:
        """Invalidate cache for a specific namespace."""
        pattern = f"{NAMESPACE_CACHE_PREFIX}*{namespace_id}*"
        CacheManager.invalidate_pattern(pattern)


# Collection-specific cache utilities
class CollectionCache:
    """Cache utilities specific to collection operations."""

    @staticmethod
    @cached_method(timeout=DEFAULT_CACHE_TIMEOUT, key_prefix=COLLECTION_CACHE_PREFIX)
    def get_collection_metadata(namespace: str, name: str, version: str) -> Optional[Dict]:
        """
        Cached collection metadata lookup.

        Args:
            namespace: Collection namespace
            name: Collection name
            version: Collection version

        Returns:
            Collection metadata dictionary or None
        """
        from pulp_ansible.app.models import CollectionVersion

        try:
            collection = CollectionVersion.objects.select_related('collection').get(
                namespace=namespace,
                name=name,
                version=version
            )
            return {
                'id': collection.pk,
                'namespace': collection.namespace,
                'name': collection.name,
                'version': collection.version,
                'created': collection.pulp_created.isoformat() if collection.pulp_created else None
            }
        except CollectionVersion.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting collection metadata: {e}")
            return None

    @staticmethod
    def invalidate_collection_cache(namespace: str, name: str) -> None:
        """Invalidate cache for a specific collection."""
        pattern = f"{COLLECTION_CACHE_PREFIX}*{namespace}*{name}*"
        CacheManager.invalidate_pattern(pattern)


# Django view caching decorators
def cache_view_page(timeout: int = DEFAULT_CACHE_TIMEOUT):
    """
    Decorator for caching entire view pages.

    Args:
        timeout: Cache timeout in seconds
    """
    return method_decorator(cache_page(timeout))


# Cache warming utilities
def warm_namespace_cache() -> None:
    """Warm up namespace-related caches."""
    from galaxy_ng.app.models import Namespace

    # Pre-load popular namespaces
    popular_namespaces = Namespace.objects.all()[:10]
    for namespace in popular_namespaces:
        try:
            NamespaceCache.get_namespace_owners(namespace.id)
        except Exception as e:
            logger.error(f"Error warming namespace cache: {e}")


def warm_collection_cache() -> None:
    """Warm up collection-related caches."""
    from pulp_ansible.app.models import CollectionVersion

    # Pre-load recently updated collections
    recent_collections = CollectionVersion.objects.select_related('collection').order_by(
        '-pulp_created'
    )[:20]

    for collection in recent_collections:
        try:
            CollectionCache.get_collection_metadata(
                collection.namespace,
                collection.name,
                collection.version
            )
        except Exception as e:
            logger.error(f"Error warming collection cache: {e}")


# Cache configuration for settings
GALAXY_CACHE_CONFIG = {
    'namespace_timeout': LONG_CACHE_TIMEOUT,
    'collection_timeout': DEFAULT_CACHE_TIMEOUT,
    'user_timeout': DEFAULT_CACHE_TIMEOUT,
    'task_timeout': SHORT_CACHE_TIMEOUT,
    'enable_cache_warming': True,
    'cache_warming_interval': 3600,  # 1 hour
}
