import logging
import os
import threading

from celery import Celery, Task
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

logger = logging.getLogger(__name__)

# No Celery worker running (e.g. on Render's free plan)? Set CELERY_INLINE=true.
# Tasks queued with .delay() then run in a background thread inside the web
# process instead of waiting forever in a queue nobody reads. Scheduled jobs
# are run by /api/cron/run/ (apps/analytics/cron.py) instead of celery beat.
CELERY_INLINE = config('CELERY_INLINE', default=False, cast=bool)


class InlineTask(Task):
    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        if not CELERY_INLINE:
            return super().apply_async(args, kwargs, task_id, producer, link, link_error, shadow, **options)

        def run():
            from django.db import connection
            try:
                self.apply(args=args, kwargs=kwargs)
            except Exception:
                logger.exception('Inline task %s failed', self.name)
            finally:
                connection.close()  # threads hold their own DB connection

        threading.Thread(target=run, daemon=True, name=f'task:{self.name}').start()
        return None


app = Celery('novelplatform', task_cls=InlineTask)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
