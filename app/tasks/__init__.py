"""Task package for Celery workers.

Keep this module lightweight so importing app.tasks does not eagerly import
the Celery app during FastAPI startup or test collection.
"""
