This is not usable or deploy able code. It is for a very old version of Django
and uses Python 2.

I used to do a lot of mail server admin and spam filtering work.

I created this around 2009 when I was approached by someone needing a custom
"secure" email spam filter with integrated email archiving. They had a
proprietary appliance doing the work but it was often 48 hours behind in
processing while running at full tilt the whole time.

I set them up with a CentOS VM with postfix, crm_114 (spam filter), Django, and
MySQL. This was all constrained by SE Linux policy (as was everything in this
environment) but I don't seem to have that code.

The emails were stored in the filesystem, the necessary metadata was stored in
MySQL, and a web interface to acces the archive was created with Django.

Normalizing the database was actually a very satisfying project. I made several
changes throughout the course of this endeavor which cut down on the amount of
data stored by an order of magnitude which helped greatly in the efficiency of
lookups as it allowed everything to be cached in RAM. This was pretty close to
"third normal form" in relational database parlance.

Another database project associated with this effort (which I was not
responsible for) had 118 columns, was not normalized at all, and caused more
trouble than I could possibly relate here.

People don't give enough credit to E.F. Codd.

You will note the use of decorators in the code to make some of the database
changes which were eventually made transparent to the code.

This code ran on a box which was essentially a mail exchange (mx) in the mail
processing flow. Mail came from outside via another server, in to postfix on
this server, was tagged as spam or not by crm_114, was passed through the
parsing code I wrote, important attributes (but NOT the entire email) were
stored in the db, a copy of the entire mail was stored in the filesystem, then
the email was routed on to another email server which hosted the mail for the
end-user to access via IMAP.

This system was written in 2009. It was occasionally modified until 2011. Then
it ran pretty much untouched until 2018. It never fell behind on mail
processing. It ended up being a very efficient and cost-effective solution to
the problem. It must have processed hundreds of millions if not billions of
emails and likely had a few million emails efficiently archived at any one time.

The biggest challenge was dealing with all of the unicode and crazy stuff the
spammers would send which for a while occasionally caused breakage of the
parsing but I got that all nailed down and it just ran and ran for years.

Upon retirement of this system and the dissolution of the organization which
used it this code became my property.

Other than the extime library present, all of the python code, templates, etc.
were written solely by me. It was considered a boring project by others and
nobody else ever wanted to touch it.

- Tracy Reed <treed@tracyreed.org>
