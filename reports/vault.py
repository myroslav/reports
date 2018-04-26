import hvac
import os


class Config(object):

    def __init__(self, config):
        self.config = config
        self.vault_addr = os.environ.get('VAULT_ADDR') or \
            self.config.get('vault', {}).get('address')
        self.token = os.environ.get('VAULT_TOKEN') or \
            self.config.get('vault', {}).get('token')
        self.base = self.config.get('brokers_keys', 'path')


class Vault(object):

    def __init__(self, config):
        self.config = Config(config)
        self.client = hvac.Client(
            url=self.config.vault_addr,
            token=self.config.token
            )

    def get(self, key, default=None):
        data = self.client.read(key).get('data')
        if data:
            return data
        return default
