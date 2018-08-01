from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import json
import logging
import re
from typing import *
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
import pytz
from requests import Session
from requests_ntlm import HttpNtlmAuth

import secret

def ticket_list_get(ses, attributes):
    # Reset timezone to Europe/London so as to not be too annoying for the user, but
    # Yes, requesting "GMT Standard Time" gives you "Europe/London". If you actually wanted GMT then
    # you should have asked for "UTC", dummy!
    r = ses.get(urljoin(attributes['url'], 'wd/logon/changeTimeZone.rails?key=GMT%20Standard%20Time'))
    r.raise_for_status()

    r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=5'))
    r.raise_for_status()
    return r.text

def ticket_list_parse(tickets: str) -> Generator[Dict[str, Any], None, None]:
    soup = BeautifulSoup(tickets, 'html.parser')
    for row in soup.find(id='listBody').find_all('tr', 'listBodyRow'):
        yield {
            'list': row,
            'list_params': json.loads(row['params']),
        }

def ticket_details_parse(body: str) -> Dict[str, Any]:
    soup = BeautifulSoup(body, 'html.parser')
    return {
        'timezone': soup.find(id='timezoneBox').span.text,
        'detail': soup.find(id='content'),
        'detail_params': json.loads(soup.find(id='original_values')['value']),
    }

DATETIME_FORMAT = '%m/%d/%Y %I:%M:%S %p'
DATETIME_TZ = pytz.timezone('Europe/London')

def parse_datetime(d: str) -> datetime.datetime:
    return DATETIME_TZ.localize(datetime.datetime.strptime(d, DATETIME_FORMAT))

def ticket_task_build(ticket: Dict[str, Any]) -> Dict[str, Any]:
    t = {
        'webdesk_created': parse_datetime(ticket['detail_params']['CreationDate852']),
        'webdesk_breach': parse_datetime(ticket['detail_params']['BreachTime850']),
        'webdesk_updated': parse_datetime(ticket['detail_params']['LastUpdate854']),
        'webdesk_key': ticket['list_params']['key'],
        'webdesk_url': ticket['url'],
        'webdesk_group': ticket['detail_params']['_CurrentAssignedGroup'],
        'webdesk_category': ticket['detail'].find(id='mainForm-Category2Display')['value'],
        'webdesk_summary': ticket['detail'].find(id='mainForm-Title54')['value'],
        'webdesk_impact': ticket['detail'].find(id='mainForm-_ImpactDisplay')['value'],
        'webdesk_customer': ticket['detail'].find(id='mainForm-RaiseUser2Display')['value'],
        'webdesk_number': int(ticket['detail'].find(id='contentTitleText').text.split()[-1]),
        'webdesk_details': re.sub(r'\s+', ' ', BeautifulSoup(ticket['detail_params']['Description49'], 'html.parser').get_text(), flags=re.UNICODE)
    }

    analyst = ticket['detail_params']['_CurrentAssignedAnalyst']
    if analyst:
        t['webdesk_analyst'] = analyst

    department = ticket['detail'].find(id='mainForm-_PHEDepartment')['value']
    if department:
        t['webdesk_department'] = department

    response = ticket['detail'].find(id='mainForm-ResponseLevel55Display')['value']
    m = re.search('(\S+)\s+(Hours|Days)', response)
    if m[2] == 'Hours':
        t['webdesk_due'] = t['webdesk_created'] + datetime.timedelta(hour=int(m[1]))
    elif m[2] == 'Days':
        due = t['webdesk_created']
        d = int(m[1])
        while d > 0:
            due += datetime.timedelta(days=1)
            if due.weekday() < 5:
                d -= 1
        t['webdesk_due'] = due

    return t

def get_tickets(attributes: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    tickets = {}

    with Session() as ses:
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
