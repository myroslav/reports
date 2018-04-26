import sys
from repoze.lru import lru_cache
from logging.config import fileConfig
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

from reports.helpers import create_db_url


BIDS_PAYMENTS_KEYS = frozenset(('bids', 'invoices'))
TENDERS_PAYMENTS_KEYS = frozenset(('tenders', 'refunds'))


class Config(object):

    def __init__(self, config, _for):
        self.config = config 
        self._for = _for
        self.api_url = '{}/api/{}'.format(
            self.get_option('api', 'host'),
            self.get_option('api', 'version')
        )

        self.thresholds = [
            float(i) for i in
            self.get_option('payments', 'thresholds')
        ]
        self.out_path = self.get_option('out', 'out_dir')
        db_name = self.get_option('db', 'name')
        self.db_url = create_db_url(
            self.get_option('db', 'host'),
            self.get_option('db', 'port'),
            self.get_option('user', 'username'),
            self.get_option('user', 'password'),
            db_name)
        self.adb_url = create_db_url(
            self.get_option('db', 'host'),
            self.get_option('db', 'port'),
            self.get_option('admin', 'username'),
            self.get_option('admin', 'password'),
            db_name)
        self.proxy_address = self.config.get("proxy_address")

    def get_option(self, section, name):
        try:
            opt = self.config.get(section, {}).get(name)
        except KeyError:
            print("No key {} in config".format(name))
            sys.exit(1)
        return opt

    @lru_cache(300)
    def _grid(self, year):
        if self._for in BIDS_PAYMENTS_KEYS:
            if year in self.config:
                return self.get_option(year, 'cdb')
            return self.get_option(str(year), 'cdb')
        elif self._for in TENDERS_PAYMENTS_KEYS:
            if year in self.config:
                return self.get_option(year, 'emall')
            return self.get_option(str(year), 'emall')
        raise NotImplemented("No payments grid for {}".format(year))

    def payments(self, grid=2017):
        return [
            float(i) for i in self._grid(grid)
        ]
