#!/usr/bin/python
import os
import sys
import time
import socket
import email.Utils
from django.db import models
from datetime import datetime
from email_archive.store_emails.models import archivedEmail

# If we are given command line args we will get the spam status and
# text from command line and file. The filename is expected to be a
# reaver_cache ID. Specify multiple filenames at a time for greater
# speed.  Otherwise read from stdin and parse it out.
# ./loadmail.py SPAM 20090812_034603_577013_2CD9524C 20090812_034603_577013_2CD91234
# or
# cat email | loadmail.py
#


def loadmail(mail):
    # Instantiate the archivedEmail object, populate fields, save to db.
    # We only want to archive domain3.net emails.
    if not mail['To'].find("domain3.net"):
        return;        
    newmail             = archivedEmail()
    newmail.toAddress   = mail['To']
    newmail.fromAddress = mail['From']
    newmail.subject     = mail['Subject']
    newmail.cacheHost   = socket.gethostname().split('.')[0]
    newmail.received    = datetime.fromtimestamp(time.mktime(email.Utils.parsedate(mail['Received'].split(';')[1].lstrip())))
    try:
        newmail.date        = datetime.fromtimestamp(time.mktime(email.Utils.parsedate(mail['Date'])))
    except TypeError:
        print "Cannot parse: ", mail['Date']
        newmail.date        = datetime.fromtimestamp(0)

    if len(sys.argv) >= 3:
        newmail.cacheID     = os.path.basename(filename)
        newmail.spamStatus  = status
        newmail.crmScore    = 0.0
    else:
        newmail.cacheID     = mail['X-CRM114-CacheID'][5:].strip()
        newmail.spamStatus  = mail['X-CRM114-Status'].split()[0]
        newmail.crmScore    = mail['X-CRM114-Status'].split()[2]


    newmail.save()

if len(sys.argv) >= 3:
    status = sys.argv[1]
    for filename in sys.argv[2:]:
        mail = email.message_from_string(open(filename,"r").read())
	loadmail(mail)
else:
    mail = email.message_from_string(sys.stdin.read())
    loadmail(mail)
