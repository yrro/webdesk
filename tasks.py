import logging
from datetime import datetime, timedelta
import re
from typing import *

import pytz
from taskw import TaskWarrior

logger = logging.getLogger(__name__)

_DATETIME_FORMAT = '%m/%d/%Y %I:%M:%S %p'
_DATETIME_TZ = pytz.timezone('Europe/London')

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
    'webdesk_number': {'label': 'WebDesk ticket number', 'type': 'numeric'},
    'webdesk_created': {'label': 'WebDesk creation ', 'type': 'string'},
    'webdesk_updated': {'label': 'WebDesk last update', 'type': 'string'},
    'webdesk_breach': {'label': 'WebDesk breach', 'type': 'string'},
    'webdesk_details': {'label': 'WebDesk details', 'type': 'string'},
    'webdesk_response': {'label': 'WebDesk resolution level', 'type': 'string'},
}

def _parse_datetime(d: str) -> datetime:
    dt = datetime.strptime(d, _DATETIME_FORMAT)
    ldt = _DATETIME_TZ.localize(dt)
    logger.debug('%s -> %s -> %s -> %s', d, dt, ldt, ldt.astimezone(pytz.utc))
    return ldt

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
    logger.debug('Adding task %s', task['webdesk_key'])
    _push_properties(task, initial=True)
    d = task['webdesk_details']
    d = d[0:100].strip() + ('…' if d[100:] else '')
    r = tw.task_add(d, **task)
    logger.log(logging.INFO+5, 'Added task %d: %s', r['id'], r['description'])

def update_task(tw: TaskWarrior, task: Dict[str, Any]) -> None:
    logger.debug('Maybe updating task %s', task['webdesk_key'])
    _push_properties(task, initial=False)
    id_, twt = tw.get_task(webdesk_key=task['webdesk_key'])
    r = twt.update(task)
    if True in r.values():
        tw.task_update(twt)
        logger.log(logging.INFO+5, 'Updated task %d (%s)', id_, ', '.join(k for k, v in r.items() if v is True))

def _push_properties(task: Dict[str, Any], initial: bool) -> None:
    entry = _parse_datetime(task['webdesk_created'])
    task['entry'] = entry

    m = re.search('(\S+)\s+(Hours|Days)', task['webdesk_response'])
    if m[2] == 'Hours':
        due = entry + timedelta(hour=int(m[1]))
    elif m[2] == 'Days':
        due = entry
        d = int(m[1])
        while d > 0:
            due += timedelta(days=1)
            if due.weekday() < 5:
                d -= 1
    task['due'] = due
