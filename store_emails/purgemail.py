#!/usr/bin/python
import os, sys
from stat import *
from django.db import models
from django.conf import settings
from datetime import datetime, timedelta
from email_archive.store_emails.models import archivedEmail

now        = datetime.today()
beginning  = datetime.fromtimestamp(0)
end        = now - timedelta(days=settings.DAYSTOKEEP)

def purgedb():
    """Delete archivedEmail objects from the beginning of time until
    daystokeep days in the past."""
    queryset   = archivedEmail.objects.all()
    purgeset   = queryset.filter(received__range=(beginning, end))
    for email in purgeset:
        print email
	try:
   	    os.unlink(settings.REAVER_CACHE+"texts/%s" % email.cacheID)
	    os.unlink(settings.REAVER_CACHE+"prob_good/%s" % email.cacheID)
	    os.unlink(settings.REAVER_CACHE+"prob_spam/%s" % email.cacheID)
	except OSError:
	    pass
    purgeset.delete()
	

def purgecache(cache):
    """Recursively descend the reaver_cache deleting files older than
    settings.DAYSTOKEEP."""
    for f in os.listdir(cache):
        pathname   = os.path.join(cache, f)
        statstruct = os.stat(pathname)
        if S_ISDIR(statstruct[ST_MODE]):
            # It's a directory, recurse into it
            purgecache(pathname)
        elif S_ISREG(statstruct[ST_MODE]):
            # It's a regular file. stat it and delete if ctime is
            # older (less than) than end.
            ctime = datetime.fromtimestamp(statstruct[ST_CTIME])
            if ctime < end:
                os.unlink(pathname)
        else:
            # Unknown file type, print a message
            print 'Skipping %s' % pathname

if __name__ == '__main__':
    purgedb()
    purgecache(settings.REAVER_CACHE)
