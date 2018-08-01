from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools
import json
import logging
import re
from typing import *
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from requests import Session
from requests_ntlm import HttpNtlmAuth

import secret

logger = logging.getLogger(__name__)

def ticket_pages(ses: Session, attributes: Dict[str, str]) -> Generator[BeautifulSoup, None, None]:
    # Reset timezone so as to not be too annoying for the user. Yes, requesting
    # "GMT Standard Time" gives you "Europe/London". If you actually wanted GMT
    # then you should have asked for "UTC", dummy! Naturally this
    # misunderstanding can be blamed on Microsoft.
    # <http://unicode.org/repos/cldr/trunk/common/supplemental/windowsZones.xml>
    r = ses.get(urljoin(attributes['url'], 'wd/logon/changeTimeZone.rails?key=GMT%20Standard%20Time'))
    r.raise_for_status()

    last_page: Optional[int] = None
    for page in itertools.count(1):
        logger.debug('Fetching tickets, page %d/%s', page, last_page if last_page is not None else '?')
        r = ses.get(urljoin(attributes['url'], 'wd/query/list.rails?class_name=IncidentManagement.Incident&query=_MyGroupIncidentWorkload&page_size=100&page={}'.format(page)))
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        m = re.match('(\S+)\s+of\s+(\S+)', soup.find(id='list-pageNumber')['watermark'])
        last_page = int(m[2])
        yield soup
        if page == last_page:
            break

def tickets_from_page(page: BeautifulSoup) -> Generator[Dict[str, Any], None, None]:
    for row in page.find(id='listBody').find_all('tr', 'listBodyRow'):
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

def ticket_task_build(ticket: Dict[str, Any]) -> Dict[str, Any]:
    d = ticket['detail_params']['Description49']
    d = BeautifulSoup(d, 'html.parser')
    d = re.sub(r'\s+', ' ', d.get_text(' '), flags=re.UNICODE)

    return {
        'webdesk_details': d,
        'webdesk_created': ticket['detail_params']['CreationDate852'],
        'webdesk_breach': ticket['detail_params']['BreachTime850'],
        'webdesk_updated': ticket['detail_params']['LastUpdate854'],
        'webdesk_key': ticket['list_params']['key'],
        'webdesk_url': ticket['url'],
        'webdesk_group': ticket['detail_params']['_CurrentAssignedGroup'],
        'webdesk_category': ticket['detail'].find(id='mainForm-Category2Display')['value'],
        'webdesk_summary': ticket['detail'].find(id='mainForm-Title54')['value'],
        'webdesk_impact': ticket['detail'].find(id='mainForm-_ImpactDisplay')['value'],
        'webdesk_customer': ticket['detail'].find(id='mainForm-RaiseUser2Display')['value'],
        'webdesk_number': int(ticket['detail'].find(id='contentTitleText').text.split()[-1]),
        'webdesk_analyst': ticket['detail_params']['_CurrentAssignedAnalyst'] or None,
        'webdesk_department': ticket['detail'].find(id='mainForm-_PHEDepartment')['value'] or None,
        'webdesk_response': ticket['detail'].find(id='mainForm-ResponseLevel55Display')['value'],
    }

def get_tickets(attributes: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    tickets = {}

    with Session() as ses:
        password = secret.get_password(attributes)
        ses.auth = HttpNtlmAuth(attributes['user'], password)

        for page in ticket_pages(ses, attributes):
            for t in tickets_from_page(page):
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
