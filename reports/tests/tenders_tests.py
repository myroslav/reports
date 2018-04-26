import unittest
from copy import copy
from reports.tests.base import BaseTenderUtilityTest
from reports.helpers import prepare_result_file_name
test_award_period = '2016-04-17T13:32:25.774673+02:00'


class ReportTendersTestCase(BaseTenderUtilityTest):

    def test_tenders_view_invalid_date(self):
        data = {
            "procurementMethodType": "aboveThresholdUA",
            "contracts": [{
                "status": "active",
                "date": "2017-12-18T22:00:00"
            }],
            "enquiryPeriod": {
                "startDate": "2016-03-11-T12:34:43"
            }
        }
        self.assertLen(0, data)

    def test_tenders_view_invalid_method(self):
        data = {
            "procurementMethodType": "aboveThresholdUA",
            "contracts": [{
                "status": "active",
                "date": "2017-12-18T22:00:00"
            }],
            "procurementMethod": "test"
        }
        self.assertLen(0, data)

    def test_tenders_view_invalid_mode(self):
        data = {
            "mode": "test",
            "procurementMethod": "open",
            "enquiryPeriod": {
                "startDate": '2016-04-17T13:32:25.774673+02:00',
            },
            'owner': 'test',
            "contracts": [
                {
                    "status": "active",
                }],
        }
        self.assertLen(0, data)

    def test_tenders_view_invalid_status(self):
        data = {
            "procurementMethod": "open",
            "enquiryPeriod": {
                "startDate": '2016-04-17T13:32:25.774673+02:00',
            },
            "contracts": [{
                "status": "unsuccessful",
            }],
        }
        self.assertLen(0, data)

    def test_tenders_view_valid(self):
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
        self.assertLen(1, data)


    def test_tenders_multilot(self):
        data = {
            "procurementMethodType": "aboveThresholdUA",
            "contracts": [{
                "status": "active",
                "date": "2017-12-18T22:00:00",
                "awardID": "award_id"
            }],
            "awards": [{
                "id": "award_id",
                "lotID": "lot_id"
            }],
            "lots": [{
                "id": "lot_id",
                "value": {
                    "currency": "UAH",
                    "amount": 100500,
                    "valueAddedTaxIncluded": False
                }
            }],
            "procuringEntity": {
                "kind": "general"
            }
        }
        self.assertLen(1, data)


class ReportTendersUtilityTestCase(BaseTenderUtilityTest):

    def setUp(self):
        super(ReportTendersUtilityTestCase, self).setUp()

    def tearDown(self):
        del self.server[self.db_name]

    def test_tenders_utility_output(self):
        data = {
            "owner": "test",
            "procurementMethod": "open",
            "enquiryPeriod": {
                "startDate": '2016-04-17T13:32:25.774673+02:00',
            },
            "contracts": [
                {
                    "status": "active",
                    "date": '2016-04-22T13:32:25.774673+02:00',
                    "dateSigned": '2016-05-22T13:32:25.774673+02:00',
                    "documents": [{
                        'datePublished': "2016-06-22T13:32:25.774673+02:00",
                    }]
                }
            ],
        }
        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)
        self.utility.run()

        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(), ','.join(self.utility.headers) + '\r\n')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReportTendersTestCase))
    suite.addTest(unittest.makeSuite(ReportTendersUtilityTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
