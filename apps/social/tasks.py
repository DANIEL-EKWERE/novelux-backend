from celery import shared_task


@shared_task
def publish_social_post(post_id):
    from .service import publish_post
    publish_post(post_id)


@shared_task
def publish_due_social_posts():
    from .service import publish_due
    return publish_due()


@shared_task
def sync_social_insights():
    from .sync import sync_all
    return sync_all()
