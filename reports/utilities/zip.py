import pyminizip
import argparse
import os.path
import ConfigParser

from reports.helpers import get_out_name
from logging import getLogger


LOGGER = getLogger("BILLING")


def compress(files, basedir, name, password):
    zipname = os.path.join(basedir, name)
    LOGGER.info("Creating archive {}".format(zipname))
    pyminizip.compress_multiple(
        [os.path.join(basedir, file) for file in files],
        os.path.join(basedir, name),
        password,
        4
    )
    return zipname


def run():
    parser = argparse.ArgumentParser(description="Openprocurement Billing")
    parser.add_argument('-f', '--files', action="append", required=True)
    parser.add_argument('-c', '--config', required=True)
    parser.add_argument('-p', '--password')
    parser.add_argument('-z', '--zipname')

    args = parser.parse_args()
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    if args.zipname:
        zip_name = args.zipname
    else:
        try:
            zip_name = get_out_name(args.files)
        except Exception:
            zip_name = '{}.zip'.format(os.path.basename(args.files[0]))
    name = compress(
        args.files,
        config.get('out', 'out_dir'),
        zip_name,
        args.password
    )
    LOGGER.info('Created: {}'.format(name))
