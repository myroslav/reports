# coding: utf-8
import mock
import os.path


test_data = {
    "procurementMethod": "open",
    "doc_type": "Tender",
    "qualificationPeriod": {
        "startDate": "2017-11-14T15:15:00+02:00"
    },
    "date": "2017-11-15T00:01:50Z",
    "owner": "test",
    "_id": "tender_id",
    "tenderID": "UA-2017-11-30",
    "dateModified": "2017-08-31T19:03:53.704712+03:00",
    "tenderPeriod": {
        "startDate": "2017-11-13T15:15:00+02:00",
    },
    "enquiryPeriod": {
        "startDate": "2017-11-13T15:15:00+02:00",
    },
    "value": {
        "currency": "UAH",
        "amount": 1000,
        "valueAddedTaxIncluded": False
    }
}


class MockCurrencyResponce(object):
    text = u'''[
     {"r030":643,"txt":"Російський рубль",
     "rate":2,"cc":"RUB","exchangedate":"16.05.2016"},
     {"r030":978,"txt":"Євро",
     "rate":2,"cc":"EUR","exchangedate":"16.05.2016"},
     {"r030":840,"txt":"Долар США",
     "rate":2,"cc":"USD","exchangedate":"16.05.2016"}]
    '''

test_config = os.path.join(os.path.dirname(__file__), 'tests.yaml')


def get_mock_parser():
    mock_parse = mock.MagicMock()
    type(mock_parse.return_value).config = mock.PropertyMock(
        return_value=test_config)
    type(mock_parse.return_value).broker = mock.PropertyMock(
        return_value='test')
    type(mock_parse.return_value).period = mock.PropertyMock(
        return_value=[])
    type(mock_parse.return_value).kind = mock.PropertyMock(
        return_value=['kind', 'general'])
    type(mock_parse.return_value).status = mock.PropertyMock(
            return_value={'action': '', 'statuses': ['complete', 'active']})

    return mock_parse
