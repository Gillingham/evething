import datetime

from celery import task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.db.models import Q

from thing.models import APIKey, TaskState

# ---------------------------------------------------------------------------
# Periodic task to perform database table cleanup
@task(name='thing.table_cleaner')
def table_cleaner():
    utcnow = datetime.datetime.utcnow()

    queued_timeout = utcnow - datetime.timedelta(minutes=120)

    # Build a QuerySet to find broken tasks
    taskstates = TaskState.objects.filter(state=TaskState.QUEUED_STATE, mod_time__lte=queued_timeout)
    for ts in taskstates:
        logger.warn('[table_cleaner] Stuck task: %d | %d | %s | %s', ts.id, ts.keyid, ts.parameter, ts.url)

    count = taskstates.update(mod_time=utcnow, next_time=utcnow, state=TaskState.READY_STATE)
    if count > 0:
        logger.warn('[table_cleaner] Reset %d broken task(s)', count)

    # Build a QuerySet to find tasks that refer to no longer existent keys
    taskstates = TaskState.objects.exclude(
        Q(keyid=-1)
        |
        Q(keyid__in=APIKey.objects.filter(valid=True).values('keyid'))
    )
    taskstates.delete()

# ---------------------------------------------------------------------------
