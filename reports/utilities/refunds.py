from logging.config import dictConfig 
from reports.core import BaseUtility, NEW_ALG_DATE
from reports.helpers import (
    thresholds_headers,
    value_currency_normalize,
    get_arguments_parser,
    Kind,
    read_config
)


class RefundsUtility(BaseUtility):

    view = 'report/tenders_owner_date'

    def __init__(
            self, broker, period, config,
            timezone="Europe/Kiev",
            kind=None
            ):
        super(RefundsUtility, self).__init__(
            broker, period, config, operation="refunds", timezone=timezone)
        self.headers = thresholds_headers(self.config.thresholds)
        self.counter = [0 for _ in range(0, 5)]
        self.counter_before = [0 for _ in range(0, 5)]
        self.new_counter = [0 for _ in range(0, 5)]
        if kind is None:
            self.kinds = ['general', 'special', 'defense', 'other', '_kind']
        else:
            self.kinds = kind

    def row(self, record):
        tender = record.get('tender', '')
        initial_date = record.get('startdate', '')
        version = 2 if initial_date > NEW_ALG_DATE else 1

        if record.get('kind') not in self.kinds and version == 1:
            self.Logger.info('Scip tender {} by kind'.format(tender))
            return

        value, rate = self.convert_value(record)

        before = initial_date < self.threshold_date
        payment = self.get_payment(value, 2016 if before else 2017)
        if before:
            p = self.config.payments(2016)
            c = self.counter_before
        else:
            p = self.config.payments(2017)
            c = self.counter
        if version == 2:
            c = self.new_counter
        for i, x in enumerate(p):
            if payment == x:
                msg = 'Refunds: refund {} for tender {} '\
                      'with value {}'.format(payment, record['tender'], value)
                self.Logger.info(msg)
                c[i] += 1

    def rows(self):
        for resp in self.response:
            self.row(resp['value'])

        for row in [
            ['before_2017'],
            self.config.payments(2016),
            self.counter_before,
            [c * v for c, v in zip(self.counter_before, self.config.payments(2016))],
            ["after 2017-01-01"],
            self.config.payments(2017),
            self.counter,
            [c * v for c, v in zip(self.counter, self.config.payments(2017))],
            ['after {}'.format(NEW_ALG_DATE)],
            self.config.payments(2017),
            self.new_counter,
            [c * v for c, v in zip(self.new_counter, self.config.payments(2017))],
        ]:
            yield row


def run():
    parser = get_arguments_parser()
    parser.add_argument(
             '--kind',
             metavar='Kind',
             action=Kind,
             help='Kind filtering functionality. '
             'Usage: --kind <include, exclude, one>=<kinds>'
             )

    args = parser.parse_args()
    config = read_config(args.config) 
    dictConfig(config)
    utility = RefundsUtility(
        args.broker, args.period,
        config, timezone=args.timezone)
    utility.run()


if __name__ == "__main__":
    run()
