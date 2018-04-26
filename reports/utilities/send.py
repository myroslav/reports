import os
import os.path
import argparse
import sys
from datetime import datetime
from logging.config import dictConfig

import smtplib
from email.mime.text import MIMEText
from email.utils import COMMASPACE

from jinja2 import Environment, PackageLoader

from logging import getLogger
from retrying import retry

from reports.storages import REGISTRY
from reports.vault import Vault
from reports.helpers import create_email_context_from_filename, read_config


YES = ['yes', 'true', 1, 'y', True]
NO = ['no', 'n', 'false', 0, False]
LOGGER = getLogger("BILLING")
SUBJECT = 'Prozorro Billing: {broker} {type} ({period})'
ENV = Environment(loader=PackageLoader('reports', 'templates'))
TEMPLATE = 'email.html'


def get_program_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        dest='config',
        required=True,
        help='Path to configuration file'
    )
    parser.add_argument(
        '-f',
        '--file',
        nargs='+',
        dest='files',
        help='Files to send'
    )
    parser.add_argument(
        '-n',
        '--notify',
        action='store_true',
        default=False,
        help='Notification flag'
    )
    parser.add_argument(
        '-e',
        '--exists',
        action='store_true',
        default=False,
        help='Send mails from existing directory; timestamp required'
    )
    parser.add_argument(
        '-t',
        '--timestamp',
        help='Initial run timestamp'
    )
    parser.add_argument(
        '-b',
        '--brokers',
        nargs='+',
        default=[],
        help='Recipients'
    )

    return parser.parse_args()


class Postman(object):

    def __init__(self, config):
        self.config = config
        self.brokers = []
        self.emails_to = self.config.get('brokers_emails')
        self.vault = Vault(self.config)

    def render_email(self, context):
        return ENV.get_template(TEMPLATE).render(context)

    def construct_mime_message(self, context):
        recipients = self.emails_to[context['broker']]
        msg = MIMEText(self.render_email(context), 'html', 'utf-8')
        msg['Subject'] = SUBJECT.format(**dict(
            broker=context['broker'],
            type=context['type'],
            period=context['period']
            ))
        msg['From'] = self.config.get('email', {}).get('verified_email')
        msg['To'] = COMMASPACE.join(recipients)
        return (recipients, msg)

    @retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
    def send_emails(self, msgs):
        try:
            self.server = smtplib.SMTP(
                    self.config.get('email', {}).get('smtp_server'),
                    self.config.get('email', {}).get('smtp_port')
                    )
            user_pass = self.vault.get(
                    self.config.get('email', {}).get('password_prefix')
                    )
            self.server.ehlo()
            if self.config.get('use_tls', True):
                self.server.starttls()
                self.server.ehlo()
            if self.config.get('email', {}).get('use_auth'):
                self.server.login(
                        user_pass.get(
                            'AWS_ACCESS_KEY_ID',
                            user_pass.get('user')),
                        user_pass.get(
                            'AWS_SECRET_ACCESS_KEY',
                            user_pass.get('password'))
                        )
        except smtplib.SMTPException as e:
            LOGGER.fatal(
                    "SMTP connection failed with error: {}. :"
                    "Generation will ran without notifications".format(e))
            self.server = None
        except Exception as e:
            LOGGER.fatal(
                    "Uncaught error while connecting to SMTP: Error: {}."
                    "Generation will ran without notifications".format(e))
            self.server = None

        try:
            for context in msgs:
                recipients, msg = self.construct_mime_message(context)
                if (not self.brokers) or (
                        self.brokers and context['broker'] in self.brokers
                        ):
                    if self.server:
                        self.server.sendmail(
                                self.config.get('email', {}).get('verified_email'),
                                recipients,
                                msg.as_string()
                                )
                        LOGGER.info('Sent mail to {}'.format(recipients))
        except smtplib.SMTPException as e:
            LOGGER.fatal("Falied to send mails. Error: {}".format(e))
        finally:
            try:
                self.server.close()
            except Exception as e:
                LOGGER.fatal("Unable to close connection "
                        "to SMTP server. Error: {}".format(e))


class Porter(object):

    def __init__(self, config, timestamp="", brokers=[]):
        self.config = config 
        storage = REGISTRY.get(self.config['storage'].get('type').strip())
        if not storage:
            LOGGER.fatal("Unsuppoted storage: {}".format(storage))
            sys.exit(1)
        self.storage = storage(config)
        self.postman = Postman(self.config)
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d/%H-%M-%S-%f")
        self.timestamp = timestamp
        self.postman.brokers = brokers

    def create_emails_context_from_existing_prefix(self):
        entries = []
        for item in self.storage.list_objects(self.timestamp):
            entry = create_email_context_from_filename(
                os.path.basename(item)
                )
            entry['link'] = self.storage.generate_presigned_url(
                    item
                    )
            entries.append(entry)
        return entries

    def upload_files(self, files):
        entries = []
        for file in files:
            entry = create_email_context_from_filename(os.path.basename(file))
            entry['link'] = self.storage.upload_file(file, self.timestamp)
            entries.append(entry)
        return entries


def run():
    args = get_program_arguments()
    config = read_config(args.config)
    dictConfig(config)
    porter = Porter(config, args.timestamp, args.brokers)

    if args.exists:
        if not args.timestamp:
            LOGGER.fatal('Timestamp is required for sending'
                         ' emails from existing files')
            sys.exit(1)
        ctx = porter.create_emails_context_from_existing_prefix()
    else:
        ctx = porter.upload_files(args.files)
    if args.notify:
        porter.postman.send_emails(ctx)


if __name__ == '__main__':
    run()
