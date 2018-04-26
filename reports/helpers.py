import os.path
import argparse
import arrow
import iso8601
import requests
import json
import re
import datetime
from yaml import load
from repoze.lru import lru_cache
from dateutil.parser import parse
from time import sleep

from retrying import retry

from logging import getLogger


RE = re.compile(r'(^.*)@(\d{4}-\d{2}-\d{2}--\d{4}-\d{2}-\d{2})?-([a-z\-]*)\.zip')
LOGGER = getLogger("BILLING")


def get_arguments_parser():
    parser = argparse.ArgumentParser(
        description="Openprocurement Billing"
    )
    report = parser.add_argument_group('Report', 'Report parameters')
    report.add_argument(
        '-c',
        '--config',
        dest='config',
        required=True,
        help="Path to config file. Required"
    )
    report.add_argument(
        '-b',
        '--broker',
        dest='broker',
        required=True,
        help='Broker name. Required'
    )
    report.add_argument(
        '-p',
        '--period',
        nargs='+',
        dest='period',
        default=[],
        help='Specifies period for billing report.\n '
             'By default report will be generated from all database'
    )
    report.add_argument(
        '-t',
        '--timezone',
        dest='timezone',
        default='Europe/Kiev',
        help='Timezone. Default "Europe/Kiev"'
    )
    return parser


def thresholds_headers(cthresholds):
    prev_threshold = None
    result = []
    thresholds = [str(t / 1000) for t in cthresholds]
    for t in thresholds:
        if not prev_threshold:
            result.append("<= " + t)
        else:
            result.append(">" + prev_threshold + "<=" + t)
        prev_threshold = t
    result.append(">" + thresholds[-1])
    return result


@lru_cache(10000)
@retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
def get_rate(currency, date, proxy_address=None):
    base_url = 'http://bank.gov.ua/NBUStatService'\
        '/v1/statdirectory/exchange?date={}&json'.format(
            iso8601.parse_date(date).strftime('%Y%m%d')
        )
    if proxy_address:
        resp = requests.get(base_url, proxies={'http': proxy_address}).text.encode('utf-8')
    else:
        resp = requests.get(base_url).text.encode('utf-8')
    doc = json.loads(resp)
    if currency == u'RUR':
        currency = u'RUB'
    rate = filter(lambda x: x[u'cc'] == currency, doc)[0][u'rate']
    sleep(15)
    return rate


def value_currency_normalize(value, currency, date, proxy_address=None):
    if not isinstance(value, (float, int)):
        raise ValueError
    rate = get_rate(currency, date, proxy_address)
    return value * rate, rate


def create_db_url(host, port, user, passwd, db_name=''):
    up = ''
    if user and passwd:
        up = '{}:{}@'.format(user, passwd)
    url = 'http://{}{}:{}'.format(up, host, port)
    if db_name:
        url += '/{}'.format(db_name)
    return url


class Kind(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):

        self.kinds = set(['general', 'special', 'defense', '_kind'])
        super(Kind, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=self.kinds,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(
            self, parser, args, values, option_string=None):
        options = values.split('=')
        self.parser = parser
        if len(options) < 2:
            parser.error("usage <option>=<kind>")
        action = options[0]
        kinds = options[1].split(',')
        try:
            getattr(self, action)(kinds)
        except AttributeError:
            self.parser.error("<option> should be one from [include, exclude, one]")

        setattr(args, self.dest, self.kinds)

    def include(self, kinds):
        for kind in kinds:
            self.kinds.add(kind)

    def exclude(self, kinds):
        for kind in kinds:
            if kind in self.kinds:
                self.kinds.remove(kind)

    def one(self, kinds):
        for kind in kinds:
            if kind not in ['general', 'special', 'defense', 'other', '_kind']:
                self.parser.error('Allowed only general, special, defense, other and _kind')
        self.kinds = set(kinds)


class Status(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):

        self.statuses = {'action': '', 'statuses': set([u'active',
                                                        u'complete',
                                                        u'active.awarded',
                                                        u'cancelled',
                                                        u'unsuccessful'
                                                        ])}
        super(Status, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=self.statuses,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(
            self, parser, args, values, option_string=None):
        options = values.split('=')
        self.parser = parser
        if len(options) < 2:
            parser.error("usage <option>=<kind>")
        action = options[0]
        statuses = options[1].split(',')
        try:
            getattr(self, action)(statuses)
        except AttributeError:
            self.parser.error("<option> should be one from [include, exclude, one]")

        setattr(args, self.dest, self.statuses)

    def include(self, sts):
        self.statuses['action'] = 'include'
        for status in sts:
            self.statuses['statuses'].add(status)

    def exclude(self, sts):
        self.statuses['action'] = 'exclude'
        for status in sts:
            if status in self.statuses:
                self.statuses['statuses'].remove(status)

    def one(self, sts):
        self.statuses['action'] = 'one'
        self.statuses['statuses'] = set(sts)


def convert_date(
        date, timezone="Europe/Kiev",
        to="UTC", format="%Y-%m-%dT%H:%M:%S.%f"
        ):
    date = arrow.get(parse(date), timezone)
    return date.to(to).strftime(format)


def prepare_report_interval(period=None):
    if not period:
        return ("", "9999-12-30T00:00:00.000000")
    if len(period) == 1:
        return (convert_date(period[0]), "9999-12-30T00:00:00.000000")
    if len(period) == 2:
        return (convert_date(period[0]), convert_date(period[1]))
    raise ValueError("Invalid period")


def prepare_result_file_name(utility):
    start, end = "", ""
    if utility.start_date:
        start = convert_date(
                utility.start_date,
                timezone="UTC",
                to="Europe/Kiev",
                format="%Y-%m-%d"
                )
    if not utility.end_date.startswith("9999"):
        end = convert_date(
                utility.end_date,
                timezone="UTC",
                to="Europe/Kiev",
                format="%Y-%m-%d"
                )
    return os.path.join(
            utility.config.out_path,
            "{}@{}--{}-{}.csv".format(
                utility.broker,
                start,
                end,
                utility.operation
                )
            )


def parse_period_string(period):
    if period:
        dates = period.split('--')
        if len(dates) > 2:
            raise ValueError("Invalid date string")
        start, end = [parse(date) for date in period.split('--')]
    else:
        end = datetime.date.today().replace(day=1)
        start = (end - datetime.timedelta(days=1)).replace(day=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def get_out_name(files):
    broker = os.path.basename(files[0].split('@')[0])
    date = os.path.basename(files[0].split('@')[1]).split('-')[:-1]
    operations = set(
        [os.path.basename(f).split('-')[-1].split('.')[0] for f in files]
    )

    out_name = '{}@{}-{}.zip'.format(
        broker, '-'.join(date), '-'.join(operations)
    )
    return out_name


def create_email_context_from_filename(file_name):
    broker, period, ops = next(iter(re.findall(RE, file_name)))
    if ops:
        ops = ops.split('-')
    type = ' and '.join(ops) if len(ops) == 2 else ', '.join(ops)
    return {
        'type': type,
        'broker': broker,
        'encrypted': bool('bids' in ops),
        'period': period
    }


def read_config(path):
    with open(path) as _in:
        return load(_in)
