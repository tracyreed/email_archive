import os
import sys

sys.path.append('/var/spool/filter')
sys.path.append('/var/spool/filter/email_archive')

os.environ['DJANGO_SETTINGS_MODULE'] = 'email_archive.settings'
os.environ['PYTHON_EGG_CACHE'] = '/var/spool/filter/.python-eggs'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
