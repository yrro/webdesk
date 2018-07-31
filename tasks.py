from taskw import TaskWarrior

from bs4 import BeautifulSoup

UDA = {
    'webdesk_key': {'label': 'WebDesk key', 'type': 'string'},
    'webdesk_url': {'label': 'WebDesk URL', 'type': 'string'},
    'webdesk_customer': {'label': 'WebDesk customer', 'type': 'string'},
    'webdesk_department': {'label': 'WebDesk department', 'type': 'string'},
    'webdesk_category': {'label': 'WebDesk category', 'type': 'string'},
    'webdesk_summary': {'label': 'WebDesk summary', 'type': 'string'},
    'webdesk_impact': {'label': 'WebDesk impact', 'type': 'string'},
    'webdesk_analyst': {'label': 'WebDesk analyst', 'type': 'string'},
    'webdesk_group': {'label': 'WebDesk assigned group', 'type': 'string'},
    'webdesk_customer': {'label': 'WebDesk customer', 'type': 'string'},
    'webdesk_number': {'label': 'WebDesk ticket number', 'type': 'numeric'},
    'webdesk_created': {'label': 'WebDesk creation ', 'type': 'date'},
    'webdesk_updated': {'label': 'WebDesk last update', 'type': 'date'},
    'webdesk_due': {'label': 'WebDesk due', 'type': 'date'},
    'webdesk_breach': {'label': 'WebDesk breach', 'type': 'date'},
}

def get_tw():
    return TaskWarrior(config_overrides={'uda': UDA}, marshal=True)

def get_tasks():
    tw = get_tw()
    tickets = {t['webdesk_key']: t for t in tw.filter_tasks({'webdesk_key.has': '-'})}
    return tickets
