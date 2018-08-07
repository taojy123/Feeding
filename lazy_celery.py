# set the default Django settings module for the 'celery' program.
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feeding.settings')

from lazypage.lazy_celery import celery_app

