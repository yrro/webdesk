import logging
from typing import *

from taskw import TaskWarrior
from taskw.task import Task

from bs4 import BeautifulSoup

_UDA = {
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
    'webdesk_details': {'label': 'WebDesk details', 'type': 'string'},
}

def get_tw() -> TaskWarrior:
    return TaskWarrior(config_overrides={'uda': _UDA}, marshal=True)

def get_tasks(tw) -> Dict[str, Dict[str, Any]]:
    return {t['webdesk_key']: t for t in tw.filter_tasks({
        'and': [
            ('webdesk_key.any', None),
        ],
        'or': [
            ('status', 'waiting'),
            ('status', 'pending'),
        ]
    })}

def add_task(tw: TaskWarrior, task: Dict[str, Any]) -> None:
    logging.debug('Adding task %s', task['webdesk_key'])
    d = task['webdesk_details']
    d = d[0:100] + ('…' if d[100:] else '')
    _push_properties(task, initial=True)

    r = tw.task_add(d, **task)
    logging.log(logging.INFO+5, 'Added task %d: %s', r['id'], r['description'])

def update_task(tw: TaskWarrior, task: Dict[str, Any]) -> None:
    logging.debug('Maybe updating task %s', task['webdesk_key'])
    _push_properties(task, initial=False)
    id_, twt = tw.get_task(webdesk_key=task['webdesk_key'])
    r = twt.update(task)
    if True in r.values():
        tw.task_update(twt)
        logging.log(logging.INFO+5, 'Updated task %d (%s)', id_, ', '.join(k for k, v in r.items() if v == True))

def _push_properties(task: Dict[str, Any], initial: bool) -> None:
    task['due'] = task['webdesk_due']
