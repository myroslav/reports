import argparse
from couchdb import Server, Session
from pbkdf2 import PBKDF2
from logging import getLogger
from logging.config import dictConfig 

from reports.helpers import create_db_url, read_config


SECURITY = {
    u'admins': {u'names': [], u'roles': ['_admin']},
    u'members': {u'names': [], u'roles': ['_admin']}
}
VALIDATE_DOC_ID = '_design/_auth'
VALIDATE_DOC_UPDATE = """function(newDoc, oldDoc, userCtx){
    if(newDoc._deleted && newDoc.tenderID) {
        throw({forbidden: 'Not authorized to delete this document'});
    }
    if(userCtx.roles.indexOf('_admin') !== -1 && newDoc._id.indexOf('_design/') === 0) {
        return;
    }
    if(userCtx.name === '%s') {
        return;
    } else {
        throw({forbidden: 'Only authorized user may edit the database'});
    }
}"""


def couchdb_connection(config):

    LOGGER = getLogger("BILLING")
    LOGGER.info("Start database initialization")

    # CouchDB connection
    db_name = config.get('db').get('name')
    db_host = config.get('db').get('host')
    db_port = config.get('db').get('port')
    admin_name = config.get('admin').get('username')
    admin_pass = config.get('admin').get('password')
    aserver = Server(
        create_db_url(db_host, db_port, admin_name, admin_pass),
        session=Session(retry_delays=range(10)))
    users_db = aserver['_users']

    username = config.get('user').get('username')
    password = config.get('user').get('password')

    user_doc = users_db.get(
        'org.couchdb.user:{}'.format(username),
        {'_id': 'org.couchdb.user:{}'.format(username)}
    )

    if not user_doc.get('derived_key', '') or PBKDF2(password, user_doc.get('salt', ''), user_doc.get('iterations', 10)).hexread(int(len(user_doc.get('derived_key', '')) / 2)) != user_doc.get('derived_key', ''):
        user_doc.update({
            "name": username,
            "roles": [],
            "type": "user",
            "password": password
        })
        LOGGER.info(
            "Updating api db main user",
            extra={'MESSAGE_ID': 'update_api_main_user'}
        )
        users_db.save(user_doc)
    if db_name not in aserver:
        aserver.create(db_name)
    db = aserver[db_name]

    SECURITY[u'members'][u'names'] = [username, ]
    if SECURITY != db.security:
        LOGGER.info(
            "Updating api db security",
            extra={'MESSAGE_ID': 'update_api_security'}
        )
        db.security = SECURITY

    auth_doc = db.get(VALIDATE_DOC_ID, {'_id': VALIDATE_DOC_ID})
    if auth_doc.get('validate_doc_update') != VALIDATE_DOC_UPDATE % username:
        auth_doc['validate_doc_update'] = VALIDATE_DOC_UPDATE % username
        LOGGER.info(
            "Updating api db validate doc",
            extra={'MESSAGE_ID': 'update_api_validate_doc'}
        )
        db.save(auth_doc)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c')
    args = parser.parse_args()
    config = read_config(args.c) 
    dictConfig(config)
    couchdb_connection(config)


if __name__ == '__main__':
    run()
