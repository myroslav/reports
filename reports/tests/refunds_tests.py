import unittest
from reports.tests.base import BaseRefundsUtilityTest
from copy import copy
from reports.utilities.refunds import NEW_ALG_DATE
from reports.helpers import prepare_result_file_name


test_award_period = '2016-04-17T13:32:25.774673+02:00'


class ReportRefundsUtilityTestCase(BaseRefundsUtilityTest):

    def test_invoices_utility_output(self):
        data = {
            "procurementMethodType": "aboveThresholdUA",
            "contracts": [{
                "status": "active",
                "date": "2017-12-18T22:00:00"
            }],
            "procuringEntity": {
                "kind": "general"
            }
        }
        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)

        self.utility.run()
        self.assertEqual(
            self.utility.new_counter, [1, 0, 0, 0, 0]
        )

        def expected_output():
            return '{}{}'.format(','.join(self.utility.headers), '\r\n') +\
                'before_2017\r\n' +\
                '{}\r\n'.format(','.join((str(i) for i in self.utility.config.payments(2016)))) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in self.utility.counter_before))
                ) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in
                              (c * v for c, v in zip(self.utility.counter_before, self.utility.config.payments(2016)))
                            ))
                ) +\
                'after 2017-01-01\r\n' + \
                '{}\r\n'.format(
                    ','.join((str(i) for i in self.utility.config.payments(2017)))
                ) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in self.utility.counter))
                ) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in
                              (c * v for c, v in zip(self.utility.counter, self.utility.config.payments(2017)))
                              ))
                ) +\
                'after {}\r\n'.format(NEW_ALG_DATE) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in self.utility.config.payments(2017)))
                ) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in self.utility.new_counter))
                ) +\
                '{}\r\n'.format(
                    ','.join((str(i) for i in
                              (c * v for c, v in zip(self.utility.new_counter, self.utility.config.payments(2017)))
                              ))
                )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.new_counter = [0 for _ in self.utility.new_counter]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 25000, 'currency': 'UAH'}})
        self.utility.db.save(doc)
        self.utility.run()
        self.assertEqual(
            self.utility.new_counter, [0, 1, 0, 0, 0]
        )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.new_counter = [0 for _ in self.utility.new_counter]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 55000, 'currency': 'UAH'}})
        self.utility.db.save(doc)

        self.utility.run()
        self.assertEqual(
            self.utility.new_counter, [0, 0, 1, 0, 0]
        )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.new_counter = [0 for _ in self.utility.new_counter]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 255000, 'currency': 'UAH'}})
        self.utility.db.save(doc)

        self.utility.run()
        self.assertEqual(
            self.utility.new_counter, [0, 0, 0, 1, 0]
        )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        self.utility.new_counter = [0 for _ in self.utility.new_counter]
        doc = self.utility.db[doc['_id']]
        doc.update({'value': {'amount': 1255000, 'currency': 'UAH'}})
        self.utility.db.save(doc)

        self.utility.run()
        self.assertEqual(
            self.utility.new_counter, [0, 0, 0, 0, 1]
        )

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), expected_output())

        del self.utility.db[doc['_id']]


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReportRefundsUtilityTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
