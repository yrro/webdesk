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

def ticket_list_get(ses):
    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=1000'))
    r.raise_for_status()
    return r.text

def ticket_list_parse(tickets):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(tickets, 'html.parser')
    for row in soup.find(id='listBody').find_all('tr', 'listBodyRow'):
        import json
        yield json.loads(row['params'])

def ticket_details_parse(body):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, 'html.parser')
    import json
    return {
        'detail_params':json.loads(soup.find(id='original_values')['value']),
    }

from urllib.parse import urljoin, urlencode
import requests
from requests_ntlm import HttpNtlmAuth

with requests.Session() as ses:
    password = get_password()
    ses.auth = HttpNtlmAuth(attributes['user'], password)

    tickets = []
    for p in ticket_list_parse(ticket_list_get(ses)):
        tickets.append({
            'url': urljoin(attributes['url'], 'wd/object/open.rails?' + urlencode([('class_name', p['launch_class_name']), ('key', p['launch_key'])])),
            'list_params': p,
        })

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(8) as ex:
        # map futures to ticket dicts
        f_to_ticket = {ex.submit(ses.get, t['url']): t for t in tickets}
        for rf in as_completed(f_to_ticket):
            rf.result().raise_for_status()
            t = f_to_ticket[rf]
            t.update(ticket_details_parse(rf.result().text))
            logging.debug(t)

# customer
# department
# category
# details
# summary
# impact
# urgency
# analyst
# created by
# created
# reference no.
