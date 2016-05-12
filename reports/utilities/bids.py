import yaml
import requests
import requests_cache
from reports.core import (
    ReportUtility,
    parse_args,
    value_currency_normalize
)
from requests.exceptions import RequestException
from yaml.scanner import ScannerError

requests_cache.install_cache('audit_cache')


class BidsUtility(ReportUtility):

    def __init__(self):
        ReportUtility.__init__(self, 'bids')
        self.headers = [u"tender", u"tenderID", u"lot",
                        u"value", u"currency", u"bid", u"bill"]
        self.view = 'report/bids_owner_date'
        self.skip_bids = set()

    def bid_date_valid(self, bid_id, audit):
        if bid_id in self.skip_bids or not audit:
            self.Logger.info('Skipped cached early bid: %s', bid_id)
            return False
        try:
            yfile = yaml.load(requests.get(self.api_url + audit['url']).text)
            initial_bids = yfile['timeline']['auction_start']['initial_bids']
            for bid in initial_bids:
                if bid['date'] < "2016-04-01":
                    self.skip_bids.add(bid['bidder'])
        except RequestException as e:
            msg = 'Request falied at getting audit file'\
                    'of {0}  bid with {1}'.format(bid_id, e)
            self.Logger.error(msg)
        except ScannerError:
            msg = 'falied to scan audit file of {} bid'.format(bid_id)
            self.Logger.error(msg)
        except KeyError:
            msg = 'falied to parse audit file of {} bid'.format(bid_id)
            self.Logger.error(msg)

        if bid_id in self.skip_bids:
            self.Logger.info('Skipped fetched early bid: %s', bid_id)
            return False
        return True

    def row(self, keys, record):
        bid = record.get(u'bid', '')
        if record.get('tender_start_date', '') < "2016-04-01" and \
                not self.bid_date_valid(bid, record.get(u'audits', '')):
            return
        row = list(record.get(col, '') for col in self.headers[:-1])
        value = float(record.get(u'value', 0))
        if record[u'currency'] != u'UAH':
            value, rate = value_currency_normalize(
                value, record[u'currency'], keys[1]
            )
            msg = "Changing value by exgange rate {} on {}"\
                  " for value {} {} in {}".format(
                        rate, keys[1], value,
                        record[u'currency'], record['tender']
                    )
            self.Logger.info(msg)

        row.append(self.get_payment(value))
        self.Logger.info(
            "Bill {} for tender {} with value {}".format(
                row[-1], row[0], row[3]
            )
        )
        return row

    def rows(self):
        for resp in self.response:
            row = self.row(resp['key'], resp["value"])
            if row:
                yield row


def run():
    utility = BidsUtility()
    owner, period, config = parse_args()
    utility.init_from_args(owner, period, config)
    utility.run()


if __name__ == "__main__":
    run()
