import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('requests.packages.urllib3').setLevel(logging.DEBUG)
logging.getLogger('requests.packages.urllib3').propagate = True

import gi

gi.require_version('Secret', '1')

from gi.repository import Secret

SCHEMA = Secret.Schema.new(
    'uk.org.robots.WebDesk',
    Secret.SchemaFlags.NONE,
    {
        'user': Secret.SchemaAttributeType.STRING,
        'url': Secret.SchemaAttributeType.STRING,
    }
)

import sys
attributes = {'user': sys.argv[1], 'url': sys.argv[2]}

if attributes['url'][-1] != '/':
    attributes['url'] += '/'

def get_password():
    password = Secret.password_lookup_sync(SCHEMA, attributes, None)
    if password is None:
        from getpass import getpass
        password = getpass('Password for \'{user}\' @ <{url}>:'.format(**attributes))
    Secret.password_store_sync(SCHEMA, attributes, Secret.COLLECTION_DEFAULT, 'WebDesk for \'{user}\' @ <{url}?'.format(**attributes), password, None)
    return password

import requests
from requests_ntlm import HttpNtlmAuth
from urllib.parse import urljoin

with requests.Session() as ses:
    password = get_password()

    ses.auth = HttpNtlmAuth(attributes['user'], get_password())
    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=10000'))
    #import ipdb; ipdb.set_trace()
    r.raise_for_status()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    for row in soup.find(id='listBody').find_all('tr', 'listBodyRow'):
        #logging.debug(row)
        import json
        params = json.loads(row['params'])
        print(urljoin(attributes['url'], 'wd/object/open.rails?class_name={launch_class_name}&key={launch_key}'.format(**params)))
