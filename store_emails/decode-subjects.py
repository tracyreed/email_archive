#!/usr/bin/python
import os, sys
from stat import *
from django.db import models
from django.conf import settings
from email.Header import decode_header
from datetime import datetime, timedelta
from email_archive.store_emails.models import archivedEmail

def decode_subjects():
    """Go through every email in the db and properly decode the subject"""
    queryset   = archivedEmail.objects.all()
    for email in queryset:
        [(string, encoding)] = decode_header(email.subject)
        if encoding != None:
            subject = string.decode(encoding)
        else:
            subject = string
        print subject
	email.save()

	
if __name__ == '__main__':
    decode_subjects()
