# Import all models FIRST to ensure they are registered with SQLAlchemy
from app.core.config import get_settings
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

settings = get_settings()

celery_app = Celery(
    "ca_nexus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Import task modules to register tasks

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=3600,
    result_extended=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_queues={
        "default": {},
        "compliance": {},
        "notifications": {},
        "workload": {},
        "outbox": {},
    },
    task_routes={
        "app.workers.compliance_tasks.*": {"queue": "compliance"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.workload_tasks.*": {"queue": "workload"},
        "app.workers.outbox_tasks.*": {"queue": "outbox"},
    },
    beat_schedule={
        "generate-compliance-cycles": {
            "task": "app.workers.compliance_tasks.generate_compliance_cycles",
            "schedule": 3600.0,
            "options": {"queue": "compliance"},
        },
        "send-compliance-reminders": {
            "task": "app.workers.compliance_tasks.send_compliance_reminders",
            "schedule": 3600.0,
            "options": {"queue": "compliance"},
        },
        "send-deadline-reminders": {
            "task": "app.workers.notification_tasks.send_deadline_reminders",
            "schedule": 1800.0,
            "options": {"queue": "notifications"},
        },
        "generate-workload-snapshots": {
            "task": "app.workers.workload_tasks.generate_daily_workload_snapshots",
            "schedule": 86400.0,
            "options": {"queue": "workload"},
        },
        "process-outbox": {
            "task": "app.workers.outbox_tasks.process_outbox_events",
            "schedule": 30.0,
            "options": {"queue": "outbox"},
        },
        "cleanup-old-outbox": {
            "task": "app.workers.outbox_tasks.cleanup_processed_outbox",
            "schedule": 86400.0,
            "options": {"queue": "outbox"},
        },
    },
    beat_scheduler="celery.beat.PersistentScheduler",
    beat_schedule_filename="/tmp/celerybeat-schedule",
)


@worker_process_init.connect
def init_worker(**kwargs):
    import asyncio

    from app.core.redis.client import init_redis

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_redis())


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    import asyncio

    from app.core.database import engine
    from app.core.redis.client import close_redis

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.run_until_complete(close_redis())
        loop.run_until_complete(engine.dispose())
    else:
        asyncio.run(close_redis())
        asyncio.run(engine.dispose())


def get_celery_app() -> Celery:
    return celery_app
