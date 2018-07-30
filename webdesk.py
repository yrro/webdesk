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

def each_ticket(ses):
    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=10000'))
    #import ipdb; ipdb.set_trace()
    r.raise_for_status()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    for row in soup.find(id='listBody').find_all('tr', 'listBodyRow'):
        import json
        params = json.loads(row['params'])
        yield {
            'key': params['launch_key'],
            'url': urljoin(attributes['url'], 'wd/object/open.rails?' + urlencode([('class_name', params['launch_class_name']), ('key', params['launch_key'])])),
        }

import requests
from requests_ntlm import HttpNtlmAuth
from urllib.parse import urljoin, urlencode

with requests.Session() as ses:
    password = get_password()

    ses.auth = HttpNtlmAuth(attributes['user'], get_password())
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(8) as ex:
        # map futures to ticket dicts
        f_to_ticket = {ex.submit(ses.get, t['url']): t for t in each_ticket(ses)}

        for rf in as_completed(f_to_ticket):
            try:
                t = f_to_ticket[rf]
                t['body'] = rf.result()
            except Exception:
                logging.exception('error fetching')
            else:
                logging.debug(t)

# customer
# department
# phone
# internal number
# category
# details
# summary
# impact
# urgency
# analyst
# created by
# created
# reference no.
