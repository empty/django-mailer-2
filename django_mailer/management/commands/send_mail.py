from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.db import connection
from django_mailer import models
from django_mailer.engine import send_all
from django_mailer.management.commands import create_handler
from optparse import make_option
import logging
import sys


# Provide a way of temporarily pausing the sending of mail.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)


class Command(NoArgsCommand):
    help = 'Iterate the mail queue, attempting to send all mail.'
    option_list = NoArgsCommand.option_list + (
        make_option('-b', '--block-size', default=500, type='int',
            help='The number of messages to iterate before checking the queue '
                'again (in case new messages have been added while the queue '
                'is being cleared).'),
        make_option('-c', '--count', action='store_true', default=False,
            help='Return the number of messages in the queue (without '
                'actually sending any)'),
    )

    def handle_noargs(self, verbosity, block_size, count, **options):
        # If this is just a count request the just calculate, report and exit.
        if count:
            queued = models.QueuedMessage.objects.non_deferred().count()
            deferred = models.QueuedMessage.objects.non_deferred().count()
            sys.stdout.write('%s queued message%s (and %s deferred message%s).'
                             '\n' % (queued, queued != 1 and 's' or '',
                                     deferred, deferred != 1 and 's' or ''))
            sys.exit()

        # Send logged messages to the console.
        logger = logging.getLogger('django_mailer')
        handler = create_handler(verbosity)
        logger.addHandler(handler)

        # if PAUSE_SEND is turned on don't do anything.
        if not PAUSE_SEND:
            send_all(block_size)
        else:
            logger = logging.getLogger('django_mailer.commands.send_mail')
            logger.warning("Sending is paused, exiting without sending "
                           "queued mail.")

        logger.removeHandler(handler)

        # Stop superfluous "unexpected EOF on client connection" errors in
        # Postgres log files caused by the database connection not being
        # explicitly closed.
        connection.close()
