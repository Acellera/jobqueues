from __future__ import absolute_import, unicode_literals
from celery import Celery


app = Celery("tasks")
app.config_from_object("jobqueues.celeryfiles.celeryconfig")

if __name__ == "__main__":
    app.start()
