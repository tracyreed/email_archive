from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404
from store_emails.models import archivedEmail
from smtplib import SMTPRecipientsRefused
from datetime import datetime, timedelta
from django.conf.urls.defaults import *
from email.Header import decode_header
from django.http import HttpResponse
from django.conf import settings
from django.http import Http404 
from django.db.models import Q
from django import forms
import email.Utils
import subprocess
import smtplib

def now():
    return datetime.today()

def minuteago():
    return now() - timedelta(minutes=1)

def hourago():
    return now() - timedelta(hours=1)

def dayago():
    return now() - timedelta(days=1)

def weekago():
    return now() - timedelta(weeks=1)

def stats(request, queryset):
    """Calculate and display a bunch of potentially interesting stats
    about the current state of the system."""
    total        = queryset.count()
    total_spam   = queryset.filter(spamStatus='SPAM').count()
    total_good   = queryset.filter(spamStatus='GOOD').count()
    total_unsure = queryset.filter(spamStatus='UNSURE').count()

    last1minute  = queryset.filter(received__range=(minuteago(), 
                                                    now())).count()
    last1hour    = queryset.filter(received__range=(hourago(), now())).count()
    last1day     = queryset.filter(received__range=(dayago(), now())).count()
    last1week    = queryset.filter(received__range=(weekago(), now())).count()

    recent_spam  = queryset.filter(spamStatus='SPAM').latest('received')
    recent_good  = queryset.filter(spamStatus='GOOD').latest('received')

    return render_to_response('stats.html', { 'total' : total, 
                                         'total_spam' : total_spam,
                                         'total_good' : total_good,
                                       'total_unsure' : total_unsure,
                                        'last1minute' : last1minute,
                                          'last1hour' : last1hour,
                                           'last1day' : last1day,
                                          'last1week' : last1week,
                                        'recent_spam' : recent_spam,
                                        'recent_good' : recent_good,
                                             }
                              )

def mail_resend(request, queryset, object_id):
    """Re-send the specified email to the recipient via SMTP. This is
    used when an email was (mis)classified as spam but we want to send
    it on to the end user anyway."""
    ourmail = queryset.get(cacheID=object_id) 
    smtp    = smtplib.SMTP(settings.RESEND_SMTP)
    try:
        smtp.sendmail(settings.RESEND_FROM,
                      ourmail.toAddress, 
                      ourmail.dump_mail())
        notice = "Mail resent to %s" % ourmail.toAddress
    except SMTPRecipientsRefused, e:
        notice = "Error sending mail: %s" % e.recipients
    smtp.quit()
    parts   = get_parts(ourmail)
    return render_to_response('mail_detail.html', { 'mail': ourmail, 
                                                   'parts': parts, 
                                                  'notice': notice
                                                  }
                             )

def mail_detail(request, queryset, object_id):
    """Display a specific email, if it exists."""
    try: 
        ourmail = queryset.get(cacheID=object_id) 
    except archivedEmail.DoesNotExist:
        raise Http404 
    parts   = []
    (parts, text) = filter_content(ourmail)
    # We really should get the character encoding of the mime part but
    # for now we will just assume everything is ascii. Some emails
    # which are supposed to be ascii still contain non-ascii chars. So
    # we filter those out here.  t is a function which we pass as an
    # argument to the translate string method which replaces non ascii
    # chars with a ?
    t    = "".join(map(chr, range(128))) + "?" * 128
    text = text.translate(t)
    return render_to_response('mail_detail.html', {'mail': ourmail, 
                                                  'parts': parts, 
                                                   'text': text
                                                   }
                              )

def get_parts(ourmail):
    """message_from_string nicely parses the email into the various
    different attachments. We assign each of these attachments to an
    array which we can return to the caller. The caller can then index
    into the array to grab whichever part it wants."""
    mail       = email.message_from_string(ourmail.dump_mail())
    parts      = []
    partnumber = 0
    for part in mail.walk():
	payload_type = (part.get_payload(decode=True),
                        part.get_content_type(), 
                        partnumber)
        partnumber = partnumber + 1
        parts.append(payload_type)
    return parts

def list_mails(request, queryset, status):
    """Generate an appropriate queryset and display a list of emails
    according to the status parameter."""
    if status == "recent":
        mails = queryset.order_by('-received')[:1000]
    elif status == "spam":
        mails = queryset.filter(spamStatus=status,
                               received__range=(hourago(), 
                                                now())).order_by('-crmScore')
    else:
        mails = queryset.filter(spamStatus=status,
                                received__range=(hourago(),
                                                 now())).order_by('crmScore')

    # Show 25 contacts per page
    paginator = Paginator(mails, 25)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        mails = paginator.page(page)
    except (EmptyPage, InvalidPage):
        mails = paginator.page(paginator.num_pages)

    return render_to_response('mail_list.html', {'mail_list': mails})

def front_page(request, queryset):
    """Just display the front page."""
    return render_to_response('base.html')

def graphs(request):
    """Display the graphs."""
    return render_to_response('graphs.html')

class searchForm(forms.Form):
    """
    A simple searchForm object.
    """
    to_email = forms.EmailField()
    from_email = forms.EmailField()

    def clean(self):
        """
	Form validator. So far we just check that at least one of the two
        fields is provided.
        """

        cleaned_data = super(searchForm, self).clean()
        to_email     = cleaned_data.get("to_email")
        from_email   = cleaned_data.get("from_email")

        if not (to_email and from_email):
            raise forms.ValidationError("Please provide at least one of To: or From: email addresses to search on.")
        return cleaned_data


def search(request):
    """Process the result of the searchForm by filtering all of the
    archivedEmail objects for the email address given."""
    # If the form has been submitted...
    if request.method == 'POST':
        # A form bound to the POST data
        form            = searchForm(request.POST)
        to_searchmail   = ""
        from_searchmail = ""

# Should figure out how to do this with form level validators 
#        if form.is_valid():
        if request.POST['to_email'] or request.POST['from_email']:
            # User entered both a from and a to address so search on both
            if request.POST['to_email'] and request.POST['from_email']:
                to_searchmail = request.POST['to_email']
                (to_user, to_domain) = to_searchmail.lower().split('@')
                from_searchmail = request.POST['from_email']
                (from_user, from_domain) = from_searchmail.lower().split('@')
                search_results = archivedEmail.objects.filter(
                    (
                        Q(toEmail__username__username__exact   = to_user) 
                        &
                        Q(toEmail__domain__domain__exact       = to_domain) 
                    )
                    &
                    (
                        Q(fromEmail__username__username__exact = from_user)
                        &
                        Q(fromEmail__domain__domain__exact     = from_domain)
                    ) 
                    ).order_by('-received')

            # Only to email provided so search just on that
            elif request.POST['to_email']:
                to_searchmail = request.POST['to_email']
                (to_user, to_domain) = to_searchmail.lower().split('@')
                search_results = archivedEmail.objects.filter(
                        Q(toEmail__username__username__exact   = to_user) 
                        &
                        Q(toEmail__domain__domain__exact       = to_domain) 
                    ).order_by('-received')

            # Only from email provided so search just on that
            elif request.POST['from_email']:
                from_searchmail = request.POST['from_email']
                (from_user, from_domain) = from_searchmail.lower().split('@')
                search_results = archivedEmail.objects.filter(
                        Q(fromEmail__username__username__exact = from_user)
                        &
                        Q(fromEmail__domain__domain__exact     = from_domain)
                    ).order_by('-received')
  
            if len(search_results) > 0:
                if to_searchmail and from_searchmail:
                    searchmail = to_searchmail + "/" + from_searchmail
                    notice     = "Emails to/from %s" % searchmail
                elif to_searchmail:
                    searchmail = to_searchmail
                    notice     = "Emails to %s" % searchmail
                elif from_searchmail:
                    searchmail = from_searchmail
                    notice     = "Emails from %s" % searchmail

                # Save for later in a django session so that we can recall this search and page through the results later.
                request.session['search_results'] = search_results
                request.session['searchmail']     = searchmail

                # Show 25 search results
                paginator = Paginator(search_results, 25) 
                # Make sure page request is an int. If not, deliver first page.
                try:
                    page = int(request.GET.get('page', '1'))
                except ValueError:
                    page = 1

		# If page request (9999) is out of range, deliver last page of
                # results.
                try:
                    search_results = paginator.page(page)
                except (EmptyPage, InvalidPage):
                    search_results = paginator.page(paginator.num_pages)


                return render_to_response('mail_list.html', 
                                          {'mail_list': search_results,
                                           'title': searchmail, 
                                           'notice':  notice
                                           }
                                          )
            else:
                return render_to_response('base.html', 
                                          {'notice': "No matching emails were found."})

    if request.session['search_results']:  
        search_results = request.session['search_results']
        searchmail     = request.session['searchmail']

        if len(search_results) > 0:
            # Show 25 search results
            paginator = Paginator(search_results, 25) 
            # Make sure page request is an int. If not, deliver first page.
            try:
                page = int(request.GET.get('page', '1'))
            except ValueError:
                page = 1

            # If page request (9999) is out of range, deliver last page of
            # results.
            try:
                search_results = paginator.page(page)
            except (EmptyPage, InvalidPage):
                search_results = paginator.page(paginator.num_pages)

            return render_to_response('mail_list.html', 
                                      {'mail_list': search_results,
                                       'title': searchmail, 
                                       }
                                      )

    # An unbound form
    form = searchForm()
    return render_to_response('base.html',
                              {'notice': "Please enter an email address to search for."})

def serve_part(request, queryset, object_id, part_id):
    """Grab the desired part_id (attachment) from the specified
    object_id (cacheID/email) and display it to the user."""
    ourmail                         = queryset.get(cacheID=object_id)     
    parts                           = get_parts(ourmail)
    (content, mimetype, partnumber) = parts[int(part_id)]
    return HttpResponse(content, mimetype=mimetype)

def learn(request, queryset, object_id, classify):
    """Train the filter based on an object_id/cacheID which is passed
    in plus what to classify it as: spam or nonspam. Pipe into
    mailfilter with the right args. Provide feedback to user by
    passing notice into the response template which contains the
    output of mailfilter."""
    ourmail = queryset.get(cacheID=object_id) 
    if classify == "spam":
        arg    = "--learnspam"
        status = "SPAM"
    else:
        arg    = "--learnnonspam"
        status = "GOOD"
    p = subprocess.Popen([settings.MAILFILTER,
                          "-u",
                          settings.CRMDIR,
                          arg,
                          "--fileprefix="+settings.CRMDIR],
                         bufsize=2048,
                         shell=False,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         close_fds=True)
    (stdout, stderr) = p.communicate(input=ourmail.dump_mail())
    notice = ""
    for line in stdout.split("\n"):
        if line.startswith("X-CRM114"):
            (header, value) = line.split(": ")
            notice = notice + value
            break
    ourmail.spamStatus = status
    ourmail.save()
    parts  = get_parts(ourmail)    
    (parts, text) = filter_content(ourmail)
    # I now have this text.translate thing in several places: views.py plus one
    # in parsemail.py. The ones here should not be necessary if they are all 
    # caught in parsemail.py
    t    = "".join(map(chr, range(128))) + "?" * 128
    text = text.translate(t)
    return render_to_response('mail_detail.html', { 'mail': ourmail, 
                                                   'parts': parts,
                                                    'text': text,
                                                  'notice': notice
                                                  }
                             )

def display_raw(request, queryset, object_id):
    """Dump the raw text of the email to the user for inspection."""
    ourmail = queryset.get(cacheID=object_id) 
    return HttpResponse(ourmail.dump_mail(), mimetype="text/plain")

def filter_content(ourmail):
    """This filters out mimetypes we do not want the user to see
    listed on the mail_detail. It also picks out the text/plain part,
    if any, to display."""
    parts = []
    text  = ""
    for content, content_type, partnumber in get_parts(ourmail):
        if content_type not in ("multipart/mixed", "multipart/alternative"):
            parts.append((content, content_type, partnumber))
        if content_type == "text/plain":
            text = content;
    return (parts, text)

class keywordForm(forms.Form):
    """A simple keywordForm object."""
    keywords = forms.CharField(widget=forms.Textarea)

def keywords(request):
    """Display/edit the blocked/whitelisted keywords."""
    if request.method == 'POST':
        # A form bound to the POST data
        form = searchForm(request.POST)
        keywords = request.POST['keywords']
        # process writing out new keywords file here
        priolist = open(settings.CRMDIR+"priolist.mfp" ,"w")
        priolist.writelines(keywords)
        priolist.close()
    # An unbound form
    form = searchForm()
    priolist = open(settings.CRMDIR+"priolist.mfp" ,"r").read()
    return render_to_response('keywords.html', { 'priolist': priolist,
                                                 }
                              )
