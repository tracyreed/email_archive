#!/usr/bin/python
#
# parsemail.py
#
# Email parser for the spam filter system. Parses email from queue and
# puts relevant attributes into database.
#
# Tracy Reed 
# 2009-2011
#
# Our first and only command line argument should be a number 0-10
# which tells us which queue this parsemail instance will be
# processing. Can also read a single email from stdin.
#

import os
import sys
import time
import socket
import subprocess
import email.Utils
from extime import Time
from django.db import models
from datetime import datetime
from django.conf import settings
from email.Utils import parseaddr
from email.Header import decode_header
from email_archive.store_emails.models import EmailDomain
from email_archive.store_emails.models import EmailAddress
from email_archive.store_emails.models import EmailUsername
from email_archive.store_emails.models import archivedEmail

# Set up so we can find our settings, libraries, etc.
os.environ['DJANGO_SETTINGS_MODULE'] = 'email_archive.settings'
QDIR="/var/spool/filter/"
sys.path.append(QDIR)

def parsemail(mail):
    """
    Instantiate the archivedEmail object, decode any utf-8, store
    only unicode in the db populate fields, save to db.
    """
    newmail                 = archivedEmail()

    for header, value in mail.items():
	# decode_header returns a list of tuples. A tuple for each encoding in
	# a particular header. In this next line I am assuming there will never
	# be more than one encoding in a given header. decode_header decodes
	# the base64 or whatever. If there is also a character set encoding
        # string.decode renders that back to unicode.
        try:
            [(string, encoding)] = decode_header(value)
        except ValueError:
            print "Warning: Caught ValueError."
            print "decode_header returned: " % decode_header(value)
            print "For header: %s and its value: %s" % (header, value)
        if encoding != None:
            try:
                mail[header] = string.decode(encoding)
            except UnicodeDecodeError:
                print "Warning: Caught UnicodeDecodeError decoding %s" % encoding
        else:
	    # Sometimes people do not specify the encoding of the header and
	    # put 8 bit or more chars in. So as a last resort we now squash
	    # everything down to 7 bits. t is a function which we pass as an
	    # argument to the translate string method # which replaces non
            # ascii chars with a ?
            t = "".join(map(chr, range(128))) + "?" * 128
            string = string.translate(t)
            mail[header] = string

    # Here's our scheme for efficiently storing email addresses. Each
    # username and domain is stored separately as an integer and an
    # email address consists of two such integers. Don't
    # over-normalize like this except in cases where you are storing
    # hundreds of thousands or millions such as we are here. Besides,
    # searching on an integer username is faster.
    #
    # Really need to factor this out into another class to make it
    # reusable in other apps as this sort of email storage is often
    # useful.
    #

    # A lot of emails do not have proper To: headers so this parseaddr and
    # split can fail.
    try:
        (user,domain)             = parseaddr(mail['To'])[1].split('@')
    except ValueError:
        (user,domain)             = ("","")

    newEmailUsername, created = EmailUsername.objects.get_or_create(
        username=user.lower())
    newEmailDomain, created   = EmailDomain.objects.get_or_create(
        domain=domain.lower())
    newEmailAddress, created  = EmailAddress.objects.get_or_create(
        username=newEmailUsername, domain=newEmailDomain)
    newmail.toEmail   = newEmailAddress

    # A lot of emails do not have proper From: headers so this parseaddr and
    # split can fail.
    try:
        (user,domain)             = parseaddr(mail['From'])[1].split('@')
    except ValueError:
        (user,domain)             = ("","")

    newEmailUsername, created = EmailUsername.objects.get_or_create(
        username=user.lower())
    newEmailDomain, created   = EmailDomain.objects.get_or_create(
        domain=domain.lower())
    newEmailAddress, created  = EmailAddress.objects.get_or_create(
        username=newEmailUsername, domain=newEmailDomain)
    newmail.fromEmail   = newEmailAddress

    newmail.cacheHost    = socket.gethostname().split('.')[0]
    try:
        newmail.cacheID  = mail['X-CRM114-CacheID'][5:].strip()
    except TypeError:
        print  mail['X-CRM114-CacheID']
    newmail.spamStatus   = mail['X-CRM114-Status'].split()[0]
    newmail.crmScore     = mail['X-CRM114-Status'].split()[2]
    # Often we are passed broken, unparseable dates. When that happens
    # we just go with the epoch.
    epoch                = "Sun, 1 Jan 1969 00:00:00 GMT"
    try:
        receivedtime     = mail['Received'].split(';')[1].lstrip()
        newmail.received = Time.fromRFC2822(receivedtime).asNaiveDatetime()
    except ValueError:
        newmail.received = Time.fromRFC2822(epoch).asNaiveDatetime()
    try:
        newmail.date     = Time.fromRFC2822(mail['Date']).asNaiveDatetime()
    except ValueError:
        newmail.date     = Time.fromRFC2822(epoch).asNaiveDatetime()
    return newmail

def honeypot(mail,raw):
    """
    Test if mail['To'] is in our list of dead email addresses which
    get a lot of spam which we use as a 'honeypot' to automatically
    train the spam filter.  If it is in the list train on it as
    spam.

    This filename should probably be factored out into the django
    setting.py file.  It should also probably be updated occasionally.
    """
    honeypots = []
    HoneypotFile = "/var/spool/filter/email_archive/store_emails/honeypots.txt"
    for line in open(HoneypotFile,"r").readlines():
        # Ignore comments
        if line.startswith("#"):
            continue
        line = line.rstrip("\n")
        if mail['To'] and line in mail['To']:
            p = subprocess.Popen([settings.MAILREAVER, 
                                  "-u", 
                                  settings.CRMDIR, 
                                  "--learnspam", 
                                  "--fileprefix="+settings.CRMDIR],
                                 bufsize   = 2048, 
                                 shell     = False, 
                                 stdin     = subprocess.PIPE, 
                                 stdout    = subprocess.PIPE, 
                                 close_fds = True
                                 )

            (stdout, stderr) = p.communicate(input=raw)
            return line

def process_mail(raw):
    """
    Convert raw string to mail object and check if it has been
    processed by crm114. If not pipe it through.
    """
    mail = email.message_from_string(raw)
    if not 'X-CRM114-CacheID' in mail:
        p = subprocess.Popen([settings.MAILREAVER, 
                              "-u", 
                              settings.CRMDIR, 
                              "--fileprefix="+settings.CRMDIR],
                             bufsize   = 2048, 
                             shell     = False, 
                             stdin     = subprocess.PIPE, 
                             stdout    = subprocess.PIPE, 
                             close_fds = True)
        (raw, stderr) = p.communicate(input=raw)
        mail = email.message_from_string(raw)
    parsemail(mail).save()
    honeypot(mail,raw)
            
if __name__ == "__main__":
    # We are called with a queue dir as an argument
    if len(sys.argv) == 2:
        queue = QDIR+sys.argv[1]
        while True:
            for filename in os.listdir(queue):
                mailfile=queue+"/"+filename
                raw = open(mailfile,"r").read()
                try:
                    process_mail(raw)
                except Exception, e:
                    errorout = open(QDIR+"/errors/"+filename,"w")
                    errorout.write(raw)
                    errorout.close()
                os.unlink(mailfile)
            # Sleep so we do not run constantly if nothing exists to process
            time.sleep(1)

    # We are fed stdin
    else:
        raw      = sys.stdin.read()
        process_mail(raw)
