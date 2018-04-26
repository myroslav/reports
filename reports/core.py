import couchdb
import os.path
import csv
import os
import yaml
import requests
from retrying import retry
from requests.exceptions import RequestException
from yaml.scanner import ScannerError
from couchdb.design import ViewDefinition
from logging import getLogger
from reports.config import Config
from reports.design import bids_owner_date, tenders_owner_date, jsonpatch,\
    tenders_lib, bids_lib
from reports.helpers import prepare_report_interval, prepare_result_file_name,\
    value_currency_normalize


VIEWS = [bids_owner_date, tenders_owner_date]
NEW_ALG_DATE = "2017-08-16"


class BaseUtility(object):

    def __init__(
            self, broker, period, config,
            timezone="Europe/Kiev", operation=""
            ):
        self.broker = broker
        self.period = period
        self.timezone = timezone
        self.operation = operation
        self.threshold_date = '2017-01-01T00:00+02:00'
        self.config = Config(config, self.operation)
        self.start_date, self.end_date = prepare_report_interval(
            self.period
        )
        self.connect_db()
        self.Logger = getLogger("BILLING")

    @retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
    def connect_db(self):
        self.db = couchdb.Database(
            self.config.db_url,
            session=couchdb.Session(retry_delays=range(10))
        )

        self.adb = couchdb.Database(
            self.config.adb_url,
            session=couchdb.Session(retry_delays=range(10))
        )

    def row(self):
        raise NotImplemented

    def rows(self):
        raise NotImplemented

    def get_payment(self, value, year=2017):
        p = self.config.payments(grid=year)
        for index, threshold in enumerate(self.config.thresholds):
            if value <= threshold:
                return p[index]
        return p[-1]

    @retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
    def _sync_views(self):
        ViewDefinition.sync_many(self.adb, VIEWS)
        _id = '_design/report'
        original = self.adb.get(_id)
        original['views']['lib'] = {
            'jsonpatch': jsonpatch,
            'tenders': tenders_lib,
            'bids': bids_lib
        }
        self.adb.save(original)

    def convert_value(self, row):
        value, curr = row.get(u'value', 0), row.get(u'currency', u'UAH')
        if curr != u'UAH':
            old = float(value)
            value, rate = value_currency_normalize(
                old, row[u'currency'], row[u'startdate'], self.config.proxy_address
            )
            msg = "Changed value {} {} by exgange rate {} on {}"\
                " is  {} UAH in {}".format(
                    old, row[u'currency'], rate,
                    row[u'startdate'], value, row['tender']
                )
            self.Logger.info(msg)
            return value, rate
        return value, "-"

    @property
    @retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
    def response(self):
        self._sync_views()
        if not self.view:
            raise NotImplemented
        return self.db.iterview(
            self.view,
            1000,
            startkey=(self.broker, self.start_date),
            endkey=(self.broker, self.end_date))

    def write_csv(self):
        if not self.headers:
            raise ValueError
        destination = prepare_result_file_name(self)
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))

        with open(destination, 'w') as out_file:
            writer = csv.writer(out_file)
            writer.writerow(self.headers)
            for row in self.rows():
                writer.writerow(row)

    def run(self):
        self.Logger.info("Start generating {} for {} for period: {}".format(
            self.operation,
            self.broker,
            self.period
            ))
        self.write_csv()


class BaseBidsUtility(BaseUtility):

    def __init__(
            self, broker, period, config,
            timezone="Europe/Kiev", operation="bids"
            ):
        self.view = 'report/bids_owner_date'
        super(BaseBidsUtility, self).__init__(
            broker, period, config, operation=operation, timezone=timezone)

    def get_initial_bids(self, audit, tender_id):
        url = audit is not None and audit.get('url')
        if not url:
            self.Logger.fatal('Invalid audit for tender id={}'.format(tender_id))
            self.initial_bids = []
            return
        try:
            yfile = yaml.load(requests.get(url).text)
            self.initial_bids = yfile['timeline']['auction_start']['initial_bids']
            self.initial_bids_for = yfile.get('tender_id', yfile.get('id', ''))
            return self.initial_bids
        except (ScannerError, KeyError, TypeError) as e:
            msg = 'Falied to scan audit file'\
                    ' for tender id={}. Error {}'.format(tender_id, e)
            self.Logger.error(msg)
        except RequestException as e:
            msg = "Request falied at getting audit file"\
                    "for tender id={0}  with error '{1}'".format(tender_id, e)
            self.Logger.info(msg)
        self.initial_bids = []

    def bid_date_valid(self, bid_id):
        for bid in self.initial_bids:
            if bid['date'] < "2016-04-01":
                self.skip_bids.add(bid['bidder'])
        if bid_id in self.skip_bids:
            self.Logger.info('Skipped fetched early bid: %s', bid_id)
            return False
        return True
