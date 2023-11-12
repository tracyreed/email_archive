from django.conf.urls.defaults import *
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import create_object
from store_emails.models import archivedEmail
from store_emails.views import *

all_emails = {'queryset': archivedEmail.objects.all()}

urlpatterns = patterns('',
    url(r'^$', front_page, all_emails),
    url(r'^email/(?P<object_id>[_\w]+)/raw$', display_raw, all_emails),
    url(r'^email/(?P<object_id>[_\w]+)/resend$', mail_resend, all_emails),
    url(r'^email/(?P<object_id>[_\w]+)/(?P<classify>spam|good)$', learn, all_emails),
    url(r'^email/(?P<object_id>[_\w]+)/(?P<part_id>\d+$)', serve_part, all_emails),
    url(r'^email/(?P<object_id>[_\w]+)$', mail_detail, all_emails),
    url(r'^(?P<status>unsure|recent|good|spam)$', list_mails, all_emails),
    url(r'^stats/', stats, all_emails),
    url(r'^graphs/', graphs),
    url(r'^search', search),
    url(r'^keywords/', keywords),
                       )
