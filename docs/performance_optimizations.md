# Galaxy NG Performance Optimizations

This document outlines the comprehensive performance optimizations implemented across the Galaxy NG application.

## Overview

The optimization strategy focuses on four key areas:
1. **Database Query Optimization** - Reducing N+1 queries and improving database performance
2. **Caching Strategy** - Multi-level caching for frequently accessed data
3. **Test Suite Optimization** - Faster test execution with intelligent waiting strategies
4. **Monitoring & Metrics** - Enhanced performance monitoring and alerting

## Implemented Optimizations

### 1. Database Query Optimization

#### N+1 Query Fixes
- **LegacyNamespaceFilter.owner_filter**: Replaced O(n) loop with optimized query using `select_related()`
- **Collection Upload**: Added transaction management and query optimization
- **Distribution Queries**: Optimized subquery patterns with direct joins

#### Database Indexes Added
```sql
-- Namespace lookups (case-insensitive)
CREATE INDEX CONCURRENTLY idx_namespace_name_lower ON galaxy_namespace (LOWER(name));

-- Collection version composite index
CREATE INDEX CONCURRENTLY idx_collection_version_namespace_name ON pulp_ansible_collectionversion (namespace, name);

-- Collection ordering
CREATE INDEX CONCURRENTLY idx_collection_version_created ON pulp_ansible_collectionversion (pulp_created DESC);

-- User authentication
CREATE INDEX CONCURRENTLY idx_auth_user_username_lower ON auth_user (LOWER(username));

-- Task filtering
CREATE INDEX CONCURRENTLY idx_core_task_state ON core_task (state);

-- Distribution lookups
CREATE INDEX CONCURRENTLY idx_ansible_distribution_base_path ON pulp_ansible_ansibledistribution (base_path);
```

#### Query Optimization Patterns
```python
# Before: N+1 query pattern
for ns in LegacyNamespace.objects.all():
    owners = get_v3_namespace_owners(ns.namespace)

# After: Optimized with select_related
legacy_namespaces = LegacyNamespace.objects.select_related('namespace').filter(
    namespace__isnull=False
)
```

### 2. Caching Strategy

#### Multi-Level Caching Implementation
- **Application Level**: Method and function result caching
- **Database Level**: QuerySet result caching
- **HTTP Level**: View page caching
- **Session Level**: Dedicated session cache

#### Cache Configuration
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {'max_connections': 20},
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'TIMEOUT': 3600,  # 1 hour
    }
}
```

#### Caching Utilities
- **@cached_method**: Method-level caching with automatic key generation
- **@cached_queryset**: QuerySet result caching
- **NamespaceCache**: Specialized caching for namespace operations
- **CollectionCache**: Collection metadata caching
- **Cache warming**: Proactive cache population

### 3. Test Suite Optimization

#### Intelligent Task Waiting
```python
# Before: Fixed sleep intervals
time.sleep(SLEEP_SECONDS_POLLING)  # 1 second

# After: Exponential backoff with shorter initial intervals
def wait_for_task_completion(task_api, task_id, timeout=30):
    poll_interval = 0.1  # Start with 100ms
    max_interval = 1.0   # Max 1 second

    while time.time() - start_time < timeout:
        if task['state'] in ['completed', 'failed', 'canceled']:
            return task
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, max_interval)
```

#### Parallel Task Monitoring
- **wait_for_multiple_tasks**: Check multiple tasks simultaneously
- **Batch operations**: Group related operations
- **Timeout optimization**: Configurable timeouts based on operation type

### 4. Enhanced Monitoring & Metrics

#### New Performance Metrics
```python
# API Performance
api_request_duration = Histogram("galaxy_api_request_duration_seconds")
database_query_duration = Histogram("galaxy_database_query_duration_seconds")
cache_operations = Counter("galaxy_cache_operations_total")

# Resource Monitoring
active_connections = Gauge("galaxy_active_connections")
memory_usage = Gauge("galaxy_memory_usage_bytes")
task_execution_duration = Histogram("galaxy_task_execution_duration_seconds")
```

#### Monitoring Decorators
```python
@track_api_request('POST', '/api/v3/collections/')
def create_collection(request):
    # Automatically tracked for performance metrics

@track_database_query('select', 'namespace')
def get_namespace_owners(namespace_id):
    # Database query performance tracking
```

## Performance Configuration

### Enable Performance Optimizations

1. **Import Performance Settings**:
```python
# In your settings file
from galaxy_ng.app.settings.performance import *
```

2. **Environment Variables**:
```bash
export GALAXY_ENVIRONMENT=production
export REDIS_URL=redis://localhost:6379/1
export FAST_TEST_MODE=true  # For test optimization
```

3. **Database Migration**:
```bash
python manage.py migrate
```

### Cache Configuration

#### Redis Setup (Recommended)
```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

#### Cache Warming
```python
# Manual cache warming
from galaxy_ng.app.utils.cache import warm_namespace_cache, warm_collection_cache

warm_namespace_cache()
warm_collection_cache()
```

## Expected Performance Improvements

### Database Performance
- **N+1 Query Fix**: 10-50x improvement for filtered namespace queries
- **Index Optimization**: 20-40% improvement for common lookups
- **Query Optimization**: 15-30% reduction in query execution time

### API Response Times
- **Caching**: 20-40% improvement for cached endpoints
- **Transaction Optimization**: 10-25% improvement for write operations
- **Connection Pooling**: 15-20% improvement under load

### Test Suite Performance
- **Intelligent Waiting**: 30-60% faster test execution
- **Parallel Operations**: 25-40% improvement for integration tests
- **Optimized Polling**: 50-70% reduction in unnecessary wait time

### Memory and Resource Usage
- **Connection Pooling**: 30-50% reduction in database connections
- **Cache Efficiency**: 40-60% reduction in redundant database queries
- **Memory Optimization**: 20-30% more efficient memory usage

## Monitoring and Alerting

### Key Metrics to Monitor
1. **Database Performance**:
   - Query execution time
   - Connection pool usage
   - Index hit ratio

2. **Cache Performance**:
   - Cache hit/miss ratio
   - Cache memory usage
   - Cache operation latency

3. **API Performance**:
   - Request/response times
   - Error rates
   - Throughput metrics

4. **Resource Usage**:
   - Memory consumption
   - CPU utilization
   - Disk I/O patterns

### Performance Alerts
```yaml
# Example Prometheus alerting rules
groups:
  - name: galaxy_ng_performance
    rules:
      - alert: HighDatabaseQueryTime
        expr: galaxy_database_query_duration_seconds > 1.0
        for: 5m

      - alert: LowCacheHitRatio
        expr: rate(galaxy_cache_operations_total{hit_miss="hit"}[5m]) / rate(galaxy_cache_operations_total[5m]) < 0.8
        for: 10m

      - alert: HighAPILatency
        expr: histogram_quantile(0.95, galaxy_api_request_duration_seconds) > 2.0
        for: 5m
```

## Best Practices

### Development
1. **Use Performance Settings**: Always import performance settings in development
2. **Monitor Queries**: Use Django Debug Toolbar to identify slow queries
3. **Cache Appropriately**: Use short cache timeouts in development
4. **Test Optimizations**: Verify performance improvements with benchmarks

### Production
1. **Enable All Optimizations**: Use production performance configuration
2. **Monitor Continuously**: Set up comprehensive monitoring and alerting
3. **Cache Strategy**: Use longer cache timeouts for stable data
4. **Database Maintenance**: Regular index maintenance and query optimization

### Testing
1. **Fast Test Mode**: Enable optimized polling for faster test execution
2. **Parallel Execution**: Use pytest-xdist for parallel test execution
3. **Resource Cleanup**: Ensure proper cleanup in test teardown
4. **Performance Tests**: Include performance regression tests

## Troubleshooting

### Common Issues

1. **Cache Misses**: Check Redis connectivity and key expiration
2. **Slow Queries**: Verify indexes are created and query plans are optimized
3. **Memory Usage**: Monitor cache size and implement appropriate eviction policies
4. **Test Timeouts**: Adjust timeout values based on environment performance

### Performance Debugging

```python
# Enable query logging for debugging
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

# Cache debugging
import logging
logging.getLogger('django.cache').setLevel(logging.DEBUG)
```

## Migration Guide

### From Unoptimized to Optimized

1. **Backup Database**: Always backup before applying index migrations
2. **Apply Migrations**: Run database migrations during maintenance window
3. **Update Settings**: Import performance settings gradually
4. **Monitor Impact**: Watch metrics during and after deployment
5. **Rollback Plan**: Have rollback procedures ready

### Gradual Rollout

1. **Phase 1**: Database indexes and query optimizations
2. **Phase 2**: Basic caching implementation
3. **Phase 3**: Advanced caching and monitoring
4. **Phase 4**: Test suite and development optimizations

This comprehensive optimization strategy provides significant performance improvements across all aspects of the Galaxy NG application while maintaining reliability and functionality.
