import unittest
from copy import copy
from reports.tests.base import BaseInvoicesUtilityTest
from reports.utilities.invoices import NEW_ALG_DATE
from reports.helpers import prepare_result_file_name

test_bids_valid = [
    [{
        "id": "bid_id",
        "status": "active",
        "date": "2017-12-01T00:00:00Z",
        "owner": "test"
    }],
    [{
        "owner": "test",
        "date": "2017-10-05T13:32:25.774673+02:00",
        "id": "44931d9653034837baff087cfc2fb5ac",
    }],

    [{
        "owner": "test",
        "date": "2017-10-10T13:32:25.774673+02:00",
        "id": "f55962b1374b43ddb886821c0582bc7f"
    }]]


test_award_period = '2016-04-17T13:32:25.774673+02:00'


class ReportInvoicesUtilityTestCase(BaseInvoicesUtilityTest):

    def test_invoices_utility_output(self):
        data = {
            "date": "2017-12-15T00:01:50+02:00",
            "procurementMethodType": "belowThreshold",
            "status": "cancelled",
            "bids": [{
                "id": "bid_id",
                "status": "active",
                "date": "2017-12-01T00:00:00Z",
                "owner": "test"
            }],
            "awards": [{
                "bid_id": "bid_id",
                "status": "active",
                "date": "2017-12-01T00:00:00Z",
            }]
        }
        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)
        self.utility.counters = {
            index: [0 for _ in range(0, 5)]
            for index in range(0, 5)
        }

        self.utility.run()
        self.assertEqual(
            self.utility.counters[3], [1, 0, 0, 0, 0]
        )

        def expected_output():
            return '{}\r\n'.format(','.join(self.utility.headers)) +\
                'after_2017-01-01\r\n' +\
                '{}\r\n'.format(','.join((str(i) for i in self.utility.counters[0]))) +\
                '{}\r\n'.format(','.join((str(i) for i in self.utility.config.payments(grid=2017)))) +\
                '{}\r\n'.format(','.join(
                    (str(c * v) for c, v in zip(self.utility.counters[0], self.utility.config.payments())))) +\
                'after_2017-08-16\r\n' +\
                '{}\r\n'.format(','.join(
                    (str(i) for i in self.utility.counters[1]))) +\
                '{}\r\n'.format(','.join(
                    (str(i) for i in self.utility.counters[2]))) +\
                '{}\r\n'.format(','.join(
                    (str(i) for i in self.utility.counters[3]))) +\
                '{}\r\n'.format(','.join(
                    (str(a - b - c) for a, b, c in zip(
                      self.utility.counters[1], self.utility.counters[2], self.utility.counters[3]
                  ))), '\r\n') +\
                '{}\r\n'.format(','.join(
                    (str(i) for i in self.utility.config.payments()))) +\
                '{}\r\n'.format(','.join(
                    (str(c * v) for c, v in
                        zip((a - b - c for a, b, c in zip(
                           self.utility.counters[1], self.utility.counters[2], self.utility.counters[3]
                        )), self.utility.config.payments())))
                )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 25000, 'currency': 'UAH'}})
        self.utility.db.save(doc)
        self.utility.counters = {
            index: [0 for _ in range(0, 5)]
            for index in range(0, 5)
        }

        self.utility.run()
        self.utility.counter = self.utility.counters[3]
        self.assertEqual(
            self.utility.counters[3], [0, 1, 0, 0, 0]
        )
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 55000, 'currency': 'UAH'}})
        self.utility.db.save(doc)
        self.utility.counters = {
            index: [0 for _ in range(0, 5)]
            for index in range(0, 5)
        }

        self.utility.run()
        self.assertEqual(
            self.utility.counters[3], [0, 0, 1, 0, 0]
        )
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.counter = [0 for _ in self.utility.config.payments()]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 255000, 'currency': 'UAH'}})
        self.utility.db.save(doc)
        self.utility.counters = {
            index: [0 for _ in range(0, 5)]
            for index in range(0, 5)
        }

        self.utility.run()
        self.assertEqual(
            self.utility.counters[3], [0, 0, 0, 1, 0]
        )
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.counter = [0 for _ in self.utility.config.payments()]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 1255000, 'currency': 'UAH'}})
        self.utility.db.save(doc)
        self.utility.counters = {
            index: [0 for _ in range(0, 5)]
            for index in range(0, 5)
        }

        self.utility.run()
        self.assertEqual(
            self.utility.counters[3], [0, 0, 0, 0, 1]
        )
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        del self.utility.db[doc['_id']]


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReportInvoicesUtilityTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
