import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('requests.packages.urllib3').setLevel(logging.DEBUG)
logging.getLogger('requests.packages.urllib3').propagate = True

import sys
attributes = {'user': sys.argv[1], 'url': sys.argv[2]}

import secret

if attributes['url'][-1] != '/':
    attributes['url'] += '/'

def ticket_list_get(ses):
    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=10000'))
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

def get_tickets():
    with requests.Session() as ses:
        password = secret.get_password(attributes)
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

        return tickets

UDA = {
    'webdesk_key': {'label': 'WebDesk key', 'type': 'string'},
    'webdesk_url': {'label': 'WebDesk URL', 'type': 'string'},
    'webdesk_customer': {'label': 'WebDesk customer', 'type': 'string'},
    'webdesk_department': {'label': 'WebDesk department', 'type': 'string'},
    'webdesk_category': {'label': 'WebDesk category', 'type': 'string'},
    'webdesk_summary': {'label': 'WebDesk category', 'type': 'string'},
    'webdesk_impact': {'label': 'WebDesk impact', 'type': 'string'},
    'webdesk_analyst': {'label': 'WebDesk analyst', 'type': 'string'},
    'webdesk_customer': {'label': 'WebDesk customer', 'type': 'string'},
    'webdesk_number': {'label': 'WebDesk ticket number', 'type': 'numeric'},
}

from taskw import TaskWarrior
tw = TaskWarrior(config_overrides={'uda': UDA}, marshal=True)
logging.debug(tw.filter_tasks({'webdesk_key.has': '-'}))

for ticket in get_tickets():
    logging.debug(ticket)
    id_, task = tw.get_task(webdesk_key=ticket['list_params']['key'])
    logging.debug(task)
    if id_ is None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(ticket['detail_params']['Description49'], 'html.parser')
        logging.debug(soup.get_text())

        tw.task_add('test', webdesk_key=ticket['list_params']['key'])

# customer
# department
# category
# details
# summary
# impact
# urgency -> due
# analyst
# customer
# created
# ticket no.
