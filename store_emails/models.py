import socket
import urllib
import datetime
import email.Utils
from django.db import models
from django.contrib import admin
from django.conf import settings
from django.db.models import permalink
from email.Header import decode_header

# CRM114 headers look like this:
#
# X-CRM114-Version: 20090423-BlameSteveJobs ( TRE 0.7.6 (BSD) ) MR-646709E3 
# X-CRM114-CacheID: sfid-20090812_165330_217024_73FC788A 
# X-CRM114-Status: SPAM  (  -5.01  )
#
# A cache file in the reaver_cache looks like this:
# 20090811_142942_675710_F33A406E
# Always 31 chars long.

class EmailUsername(models.Model):
    """
    Store each username just once along with an integer ID which is
    automatically created by the ORM.
    """

    username = models.CharField(max_length=64);

class EmailDomain(models.Model):
    """
    Store each domain just once along with an integer ID which is
    automatically created by the ORM.
    """

    domain = models.CharField(max_length=64);

class EmailAddress(models.Model):
    """
    Store each email address as a combination of integer@integer
    foreign key relationships to the emailusername and emaildomain
    classes. Django automatically links the integer ID columns for us.

    This is much more space efficient and faster for lookup than
    storing each individual email address as a string.

    Having a username integer foreign key is way over-normalizing in
    most cases but since we store millions of them and I already have
    a domain I figured I would go with a username also. It really
    doesn't save us much space or anything.

    """    

    username = models.ForeignKey('EmailUsername')
    domain   = models.ForeignKey('EmailDomain')

spamStatusChoices = (
    ('g', 'GOOD'),
    ('s', 'SPAM'),
    ('u', 'UNSURE'),
    )

class archivedEmail(models.Model):
    date        = models.DateTimeField()
    received    = models.DateTimeField(db_index=True)
    crmScore    = models.FloatField()
    spamStatus  = models.CharField(max_length=6, choices=spamStatusChoices, db_index=True)
    cacheHost   = models.CharField(max_length=24)
    cacheID     = models.CharField(max_length=31, primary_key=True)
    toEmail     = models.ForeignKey(EmailAddress, related_name="toEmails")
    fromEmail   = models.ForeignKey(EmailAddress, related_name="fromEmails")

    class Meta:
        ordering = ('-received',)

    def __unicode__(self):
        return self.subject

    def get_absolute_url(self):
        return "email/%s/" % self.cacheID

    def dump_mail(self):
        if self.cacheHost != socket.gethostname().split('.')[0]:
            try:
                themail = urllib.urlopen("http://%s/email/%s/raw" % (self.cacheHost, self.cacheID)).read()
            except:
                return "No body on remote server"
        else:
            try:
                themail = open(settings.REAVER_CACHE+"texts/%s" % self.cacheID ,"r").read()
            except IOError:
                return "No body"
	return themail

    def delete(self):
        try:
            os.remove(settings.REAVER_CACHE+'prob_good/' + self.cacheID)
            os.remove(settings.REAVER_CACHE+'prob_spam/' + self.cacheID)
            os.remove(settings.REAVER_CACHE+'texts/'     + self.cacheID)
        except:
            # We don't care if the file isn't there.
            pass
        # Call parent class delete method which we are overriding here
        models.Model.delete(self)

    def get_subject(self):
        if self.cacheHost != socket.gethostname().split('.')[0]:
            try:
                f = urllib.urlopen("http://%s/email/%s/raw" % (self.cacheHost, self.cacheID)).read()
            except:
                return "File not found on remote server"
        else:
            try:
                f = open(settings.REAVER_CACHE+"texts/%s" % self.cacheID ,"r").read()
            except IOError:
                return "File not found"
        cachemail = email.message_from_string(f)
        subject   = decode_header(cachemail['Subject'])[0][0]
        t         = "".join(map(chr, range(128))) + "?" * 128
        subject   = subject.translate(t)
        return(subject)
    subject = property(get_subject)

    def get_toAddress(self):
        username = self.toEmail.username.username
        domain   = self.toEmail.domain.domain
        return(username+"@"+domain)        
    toAddress = property(get_toAddress)

    def get_fromAddress(self):
        username = self.fromEmail.username.username
        domain   = self.fromEmail.domain.domain
        return(username+"@"+domain)        
    fromAddress = property(get_fromAddress)

class archivedEmailAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 
                    'subject', 
                    'toAddress', 
                    'fromAddress', 
                    'date', 
                    'crmScore')
    list_filter  = ('date', 'fromAddress')
