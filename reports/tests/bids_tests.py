import unittest
from copy import copy
from couchdb import ServerError
from reports.tests.base import BaseBidsUtilityTest
from reports.helpers import prepare_result_file_name

test_bids_invalid = [
    [{
        "owner": "test",
        "date": "2016-03-17T13:32:25.774673+02:00",
        "id": "44931d9653034837baff087cfc2fb5ac",
    }],
    [{
        "status": "invalid",
        "owner": "test",
        "date": "2016-04-17T13:32:25.774673+02:00",
        "id": "44931d9653034837baff087cfc2fb5ac"
    }]
]

test_bids_valid = [
    [{
        "owner": "test",
        "date": "2017-09-17T13:32:25.774673+02:00",
        "id": "44931d9653034837baff087cfc2fb5ac",
        "status": "active"
    }],
    [{
        "owner": "test",
        "date": "2017-09-05T13:32:25.774673+02:00",
        "id": "44931d9653034837baff087cfc2fb5ac",
        "status": "active"
    }],

    [{
        "owner": "test",
        "date": "2017-09-10T13:32:25.774673+02:00",
        "id": "f55962b1374b43ddb886821c0582bc7f",
        "status": "active"
    }]]


test_award_period = '2016-04-17T13:32:25.774673+02:00'


class ReportBidsViewTestCase(BaseBidsUtilityTest):

    def test_bids_view_invalid_date(self):
        data = {
            "awardPeriod": {
                "startDate": test_award_period,
            },
            'owner': 'test',
            "bids": test_bids_invalid[0],
        }
        self.assertLen(0, data)

    def test_bids_view_invalid_mode(self):
        data = {
            'mode': 'test',
            "awardPeriod": {
                "startDate": test_award_period,
            },
            'owner': 'test',
            "bids": test_bids_valid[0],
        }
        self.assertLen(0, data)

    def test_bids_view_invalid_status(self):
        data = {
            "procurementMethod": "open",
            "awardPeriod": {
                "startDate": test_award_period,
            },
            'owner': 'test',
            'bids': test_bids_invalid[1],
        }
        self.assertLen(0, data)

    def test_bids_view_invalid_method(self):
        data = {
            "procurementMethod": "test",
            "awardPeriod": {
                "startDate": test_award_period,
            },
            'owner': 'test',
            'bids': test_bids_valid[0],
        }
        self.assertLen(0, data)

    def test_bids_view_valid(self):
        data = {
            "date": "2017-12-15T00:01:50+02:00",
            "qualificationPeriod": {
                "startDate": "2017-11-15",
            },
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
                "date": "2017-11-16"
            }]
        }
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(1000, response[0]['value']['value'])
        self.assertEqual(
            "bid_id", response[0]['value']['bid']
        )
        self.assertEqual(
            "tender_id", response[0]['value']['tender']
        )
        self.assertEqual(
            "UA-2017-11-30", response[0]['value']['tenderID']
        )
        self.assertEqual(
            u"UAH", response[0]['value']['currency']
        )

    def test_bids_view_period(self):
        self.utility.owner = 'test'
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
                "date": "2017-12-02T00:00:00Z"
            }]
        }

        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)

        self.utility.start_date = ''
        self.utility.end_date = '9999-12-30T00:00:00.000000'
        self.assertEqual(1, len(list(self.utility.response)))

        disclosure_date = doc["qualificationPeriod"]["startDate"]
        tender_date = doc["date"]

        self.utility.start_date = min(disclosure_date, tender_date)
        self.utility.end_date = '9999-12-30T00:00:00.000000'
        self.assertEqual(1, len(list(self.utility.response)))

        self.utility.start_date = max(disclosure_date, tender_date)
        self.utility.end_date = '9999-12-30T00:00:00.000000'
        self.assertEqual(0, len(list(self.utility.response)))

        self.utility.start_date = min(disclosure_date, tender_date)
        self.utility.end_date = min(disclosure_date, tender_date)
        self.assertEqual(0, len(list(self.utility.response)))

        self.utility.start_date = min(disclosure_date, tender_date)
        self.utility.end_date = max(disclosure_date, tender_date)
        self.assertEqual(1, len(list(self.utility.response)))

        self.utility.start_date = max(disclosure_date, tender_date)
        self.utility.end_date = min(disclosure_date, tender_date)
        self.utility.response
        self.assertRaises(ServerError)

    def test_bids_no_lots(self):
        # state 3
        data = {
            "date": "2017-12-15T00:01:50Z",
            "procurementMethodType": "belowThreshold",
            "status": "cancelled",
            "bids": [{
                "id": "bid_id",
                "status": "active",
                "date": "2017-12-03T00:00:00Z",
                "owner": "test"
            }],
            "awards": [{
                "bid_id": "bid_id",
                "status": "active",
                "date": "2017-12-02T00:00:00Z"
            }]
        }
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 3)
        del self.utility.db["tender_id"]

        # state 4
        data["status"] = "active"
        self.assertLen(2, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 1)
        self.assertEqual(response[1]["key"][-1], 4)
        del self.utility.db["tender_id"]

    def test_bids_multilot(self):
        data = {
            "procurementMethodType": "belowThreshold",
            "lots": [{
                "id": "lot_id",
                "date": "2017-12-01T00:00:00Z",
                "status": "active",
                "value": {
                    "currency": "UAH",
                    "amount": 100500,
                    "valueAddedTaxIncluded": False
                }
            }],
            "awards": [{
                "bid_id": "bid_id",
                "status": "active",
                "lotID": "lot_id",
                "date": "2017-12-01T00:00:00Z"
            }],
            "bids": [{
                "id": "bid_id",
                "status": "active",
                "date": "2017-12-01T00:00:00Z",
                "owner": "test",
                "lotValues": [{
                    "relatedLot": "lot_id"
                }]
            }],
        }
        self.assertLen(2, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 1)
        self.assertEqual(response[1]["key"][-1], 4)
        del self.utility.db["tender_id"]

        data["status"] = "unsuccessful"
        self.assertLen(2, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 1)
        self.assertEqual(response[1]["key"][-1], 2)
        del self.utility.db["tender_id"]

        data["date"] = "2017-12-15T00:00:00Z"
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 3)
        del self.utility.db["tender_id"]

        data["lots"][0]["status"] = "cancelled"
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 3)
        del self.utility.db["tender_id"]

        data["lots"][0]["date"] = "2017-11-15T00:00:00Z"
        self.assertLen(2, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["key"][-1], 1)
        self.assertEqual(response[1]["key"][-1], 2)

    def test_bids_with_revisions(self):
        # no revisions
        data = {
            "date": "2017-12-15T00:01:50Z",
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
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["value"]["initialDate"], "")
        del self.utility.db["tender_id"]

        data["revisions"] = [
            {
                "date": "2017-11-30T00:00:00Z",
                "changes": [
                    {
                        "path": "/bids/0/date",
                        "op": "replace",
                        "value": "2017-11-01T00:00:00Z"
                    }
                ]
            }
        ]
        self.assertLen(1, data)
        response = list(self.utility.response)
        self.assertEqual(response[0]["value"]["initialDate"], data["revisions"][0]["date"])


class ReportBidsUtilityTestCase(BaseBidsUtilityTest):

    def test_bids_utility_output(self):
        data = {
            "awardPeriod": {
                "startDate": test_award_period,
            },
            'owner': 'test',
            'bids': test_bids_valid[0],
        }
        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)

        self.utility.run()
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(),
                             ','.join(self.utility.headers) + '\r\nafter_2017-01-01\r\n')

    def test_bids_utility_output_with_lots(self):
        data = {
            "enquiryPeriod": {
                "startDate": '2016-04-17T13:32:25.774673+02:00',
            },
            "awardPeriod": {
                "startDate": test_award_period,
            },

            "lots": [
                {
                    "status": "active",
                    "id": "324d7b2dd7a54df29bad6d0b7c91b2e9",
                    "value": {
                        "currency": "UAH",
                        "amount": 2000,
                        "valueAddedTaxIncluded": False,
                    },
                }
            ],
            "bids": [
                {
                    "date": "2016-04-07T16:36:58.983102+03:00",
                    "owner": "test",
                    "id": "a22ef2b1374b43ddb886821c0582bc7dk",
                    "lotValues": [
                        {
                            "relatedLot": "324d7b2dd7a54df29bad6d0b7c91b2e9",
                            "date": "2016-04-07T16:36:58.983062+03:00",
                        }
                    ],
                }
            ],
        }
        doc = copy(self.test_data)
        doc.update(data)
        self.utility.db.save(doc)

        self.utility.run()
        with open(prepare_result_file_name(self.utility), 'rb') as file:
            self.assertEqual(file.read(),
                             ','.join(self.utility.headers) + '\r\nafter_2017-01-01\r\n')

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReportBidsViewTestCase))
    suite.addTest(unittest.makeSuite(ReportBidsUtilityTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
