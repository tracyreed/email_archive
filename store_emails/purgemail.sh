#!/bin/sh

# Days of mail to keep
DAYS=4

echo "delete from store_emails_archivedemail where received < DATE_SUB(curdate(), interval $DAYS day);" | mysql email_archive
find /var/spool/crm/reaver_cache/ -print -ctime +$DAYS -type f -exec rm {} +
