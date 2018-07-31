from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
import requests
from requests_ntlm import HttpNtlmAuth

import secret

def ticket_list_get(ses, attributes):
    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=1000'))
    r.raise_for_status()
    return r.text

def ticket_list_parse(tickets):
    soup = BeautifulSoup(tickets, 'html.parser')
    for row in soup.find(id='listBody').find_all('tr', 'listBodyRow'):
        yield {
            'list': row,
            'list_params': json.loads(row['params']),
        }

def ticket_details_parse(body):
    soup = BeautifulSoup(body, 'html.parser')
    return {
        'detail': soup.find(id='content'),
        'detail_params': json.loads(soup.find(id='original_values')['value']),
    }

def ticket_task_build(ticket):
    t = {
        'webdesk_created': ticket['detail_params']['CreationDate852'],
        'webdesk_breach': ticket['detail_params']['BreachTime850'],
        'webdesk_key': ticket['list_params']['key'],
        'webdesk_url': ticket['url'],
        'webdesk_group': ticket['detail_params']['_CurrentAssignedGroup'],
        'webdesk_category': ticket['detail'].find(id='mainForm-Category2Display')['value'],
        'webdesk_summary': ticket['detail'].find(id='mainForm-Title54')['value'],
        'webdesk_impact': ticket['detail'].find(id='mainForm-_ImpactDisplay')['value'],
        'webdesk_customer': ticket['detail'].find(id='mainForm-RaiseUser2Display')['value'],
        'webdesk_number': int(ticket['detail'].find(id='contentTitleText').text.split()[-1]),
        'webdesk_details': BeautifulSoup(ticket['detail_params']['Description49'], 'html.parser').get_text()
    }

    analyst = ticket['detail_params']['_CurrentAssignedAnalyst']
    if analyst:
        t['webdesk_analyst'] = analyst

    department = ticket['detail'].find(id='mainForm-_PHEDepartment')['value']
    if department:
        t['webdesk_department'] = department

    response = ticket['detail'].find(id='mainForm-ResponseLevel55Display')['value']
    m = re.search('(\d+)\s+(Hours|Days)', response)
    assert m
    if m:
        t['webdesk_due'] = m.groups()

    return t

def get_tickets(attributes):
    tickets = {}

    with requests.Session() as ses:
        password = secret.get_password(attributes)
        ses.auth = HttpNtlmAuth(attributes['user'], password)

        for t in ticket_list_parse(ticket_list_get(ses, attributes)):
            tickets[t['list_params']['key']] = {
                'url': urljoin(
                    attributes['url'],
                    'wd/object/open.rails?'
                        + urlencode([
                            ('class_name', t['list_params']['launch_class_name']),
                            ('key', t['list_params']['launch_key'])
                        ])
                ),
                **t,
            }

        with ThreadPoolExecutor(8) as ex:
            # map futures to ticket dicts
            f_to_ticket = {ex.submit(ses.get, t['url']): t for t in tickets.values()}
            for rf in as_completed(f_to_ticket):
                rf.result().raise_for_status()
                t = f_to_ticket[rf]
                t.update(ticket_details_parse(rf.result().text))

    for t in tickets.values():
        t['task'] = ticket_task_build(t)

    return tickets
