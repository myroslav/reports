import os
import csv
from yaml import load
from logging.config import dictConfig 
from reports.core import BaseBidsUtility, NEW_ALG_DATE
from reports.helpers import value_currency_normalize,\
    get_arguments_parser, prepare_result_file_name, read_config


HEADERS = [
    u"tender", u"tenderID", u"lot",
    u"value", u"currency", u"bid",
    u'rate', u"bill", u"state"
]


class BidsUtility(BaseBidsUtility):

    headers = HEADERS

    def row(self, record):
        startdate = record.get('startdate', '')
        version = 1 if startdate < NEW_ALG_DATE else 2
        state = record.get('state', '')
        row = list(record.get(col, '') for col in self.headers[:-3])
        value, rate = self.convert_value(record)
        r = str(rate) if rate else ''
        row.append(r)
        payment = self.get_payment(value)
        row.append(payment)
        if state:
            row.append(state)
        self.Logger.info(
            "Bids: bill {} for tender {} with value {}".format(
                payment, row[0], value
            )
        )
        return row, version

    def write_csv(self):
        second_version = []
        splitter = [u'after {}'.format(NEW_ALG_DATE)]
        destination = prepare_result_file_name(self)
        if not self.headers:
            raise ValueError
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        with open(destination, 'w') as out_file:
            writer = csv.writer(out_file)
            writer.writerow(self.headers)
            writer.writerow(['after_2017-01-01'])
            for row, ver in self.rows():
                if ver == 1:
                    writer.writerow(row)
                else:
                    second_version.append(row)
            if second_version:
                writer.writerow(splitter)
                for row in second_version:
                    writer.writerow(row)

    def rows(self):
        for resp in self.response:
            row, ver = self.row(resp["value"])
            if row:
                yield row, ver


def run():
    parser = get_arguments_parser()
    args = parser.parse_args()
    config = read_config(args.config)
    dictConfig(config)
    utility = BidsUtility(args.broker, args.period,
                          config, timezone=args.timezone)
    utility.run()


if __name__ == "__main__":
    run()
