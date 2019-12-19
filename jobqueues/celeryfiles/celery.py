from __future__ import absolute_import, unicode_literals
from celery import Celery


# Start with:
# docker run -d -p 5462:5672 rabbitmq
# celery --app=jobqueues.celeryfiles.celery worker --loglevel=info -Q gpu,celery -c 1

app = Celery("tasks")
app.config_from_object("jobqueues.celeryfiles.celeryconfig")

if __name__ == "__main__":
    app.start()
