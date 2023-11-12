#!/usr/bin/python
import os, sys
from stat import *
from django.db import models
from django.conf import settings
from email.Header import decode_header
from datetime import datetime, timedelta
from email_archive.store_emails.models import archivedEmail
from email.Utils import parseaddr
from email_archive.store_emails.models import EmailDomain
from email_archive.store_emails.models import EmailAddress
from email_archive.store_emails.models import EmailUsername
from email_archive.store_emails.models import archivedEmail

def decode_subjects():
    """Go through every email in the db set the to/from IDs"""
    queryset   = archivedEmail.objects.all()
    for email in queryset:

        print email.toAddress
        (user,domain)             = parseaddr(email.toAddress)[1].split('@')
        newEmailUsername, created = EmailUsername.objects.get_or_create(
            username=user.lower())
        newEmailDomain, created   = EmailDomain.objects.get_or_create(
            domain=domain.lower())
        newEmailAddress, created  = EmailAddress.objects.get_or_create(
            username=newEmailUsername, domain=newEmailDomain)
        email.toEmail   = newEmailAddress
        print email.toEmail

        print email.fromAddress
        (user,domain)             = parseaddr(email.fromAddress)[1].split('@')
        newEmailUsername, created = EmailUsername.objects.get_or_create(
            username=user.lower())
        newEmailDomain, created   = EmailDomain.objects.get_or_create(
            domain=domain.lower())
        newEmailAddress, created  = EmailAddress.objects.get_or_create(
            username=newEmailUsername, domain=newEmailDomain)
        email.fromEmail   = newEmailAddress
        print email.fromEmail

        email.save()
	
if __name__ == '__main__':
    decode_subjects()
