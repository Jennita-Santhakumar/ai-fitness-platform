from app.worker import celery_app, add


def test_add_task_direct_execution():
    """Verify add task executes directly as a Python callable."""
    result = add(2, 3)
    assert result == 5
    assert add(10, -4) == 6


def test_add_task_celery_eager_execution():
    """Verify Celery task delay invocation works in eager/test mode."""
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    async_result = add.delay(7, 8)
    assert async_result.successful()
    assert async_result.result == 15
    celery_app.conf.update(task_always_eager=False)


def test_celery_configuration():
    """Verify Celery app has proper serializers and timezone settings."""
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
