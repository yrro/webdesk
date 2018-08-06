import logging
import os
import sys

import webdesk
import tasks

logger = logging.getLogger(__name__)

def main(argv) -> int:
    logging.addLevelName(logging.INFO+5, 'NOTICE')
    logging.basicConfig()

    log_level = os.environ.get('PYTHONLOGLEVEL', str(logging.INFO))
    try:
        log_level = int(log_level)
    except ValueError:
        pass
    logging.getLogger().setLevel(log_level)

    attributes = {'user': argv[1], 'url': argv[2]}
    if not attributes['url'].endswith('/'):
        attributes['url'] += '/'

    logger.info('Fetching tickets from WebDesk...')
    tickets = webdesk.get_tickets(attributes)

    tw = tasks.get_tw()
    logger.debug('Getting tickets from TaskWarrior...')
    tasks_ = tasks.get_tasks(tw)

    new_tasks = tickets.keys() - tasks_.keys()
    existing_tasks = tickets.keys() & tasks_.keys()
    missing_tasks = tasks_.keys() - tickets.keys()
    logger.info('%d new, %d existing and %d missing tasks', len(new_tasks), len(existing_tasks), len(missing_tasks))

    for k in new_tasks:
        tasks.add_task(tw, tickets[k]['task'])

    for k in existing_tasks:
        tickets[k]['task']['webdesk_unhide'] = 1
        tasks.update_task(tw, tickets[k]['task'])

    if missing_tasks:
        logger.info('Fetching missing tickets from WebDesk...')
    missing_tickets = webdesk.get_tickets(attributes, {k: v for k, v in tasks_.items() if k in missing_tasks})
    for k, v in missing_tickets.items():
        v['task']['webdesk_hidden'] = 1
        tasks.update_task(tw, v['task'])

        if v['task']['webdesk_status'] == 'Closed':
            tasks.complete_task(tw, v['task'])

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
