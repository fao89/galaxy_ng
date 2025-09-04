"""
Task function registry for PostgreSQL-based task system.
"""
from typing import Callable, Dict, Any


class TaskRegistry:
    """
    Registry for task functions.
    """
    
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
    
    def register(self, name: str, func: Callable):
        """Register a task function."""
        self._functions[name] = func
    
    def get(self, name: str) -> Callable:
        """Get a registered function."""
        return self._functions.get(name)
    
    def __contains__(self, name: str) -> bool:
        """Check if function is registered."""
        return name in self._functions
    
    def list_functions(self) -> list:
        """List all registered functions."""
        return list(self._functions.keys())


# Global registry instance
task_registry = TaskRegistry()


def task(name: str = None):
    """
    Decorator to register task functions.
    
    Usage:
        @task()
        def my_task_function(arg1, arg2):
            # task implementation
            pass
    """
    def decorator(func: Callable):
        task_name = name or func.__name__
        task_registry.register(task_name, func)
        return func
    
    return decorator