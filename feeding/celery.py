
import os
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feeding.settings')

from lazypage.celery_init import celery_app


