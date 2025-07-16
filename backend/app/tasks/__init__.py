# app/tasks/__init__.py
# Module pour les tâches programmées et le scheduler

from .simple_scheduler import (
    simple_scheduler,
    start_scheduler,
    stop_scheduler,
    restart_scheduler,
    get_scheduler_status,
    is_scheduler_running,
    get_scheduler_health,
    get_scheduler_instance
)

__all__ = [
    'simple_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'restart_scheduler',
    'get_scheduler_status',
    'is_scheduler_running',
    'get_scheduler_health',
    'get_scheduler_instance'
]