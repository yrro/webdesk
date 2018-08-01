import logging
import sys

import webdesk
import tasks

def main(argv) -> int:
    logging.addLevelName(logging.INFO+5, 'NOTICE')
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.DEBUG)
    logging.getLogger('requests.packages.urllib3').propagate = True

    attributes = {'user': argv[1], 'url': argv[2]}
    if not attributes['url'].endswith('/'):
        attributes['url'] += '/'

    logging.info('Fetching tickets from WebDesk...')
    tickets = webdesk.get_tickets(attributes)

    tw = tasks.get_tw()
    logging.debug('Getting tickets from TaskWarrior...')
    tasks_ = tasks.get_tasks(tw)

    new_tasks = tickets.keys() - tasks_.keys()
    existing_tasks = tickets.keys() & tasks_.keys()
    missing_tasks = tasks_.keys() - tickets.keys()
    logging.info('%d new, %d existing and %d missing tasks', len(new_tasks), len(existing_tasks), len(missing_tasks))

    for k in new_tasks:
        tasks.add_task(tw, tickets[k]['task'])

    for k in existing_tasks:
        tasks.update_task(tw, tickets[k]['task'])

    for k in missing_tasks:
        logging.notice('Checking task <%s> for completion - not implemented', k)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
