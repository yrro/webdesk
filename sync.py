import logging
import sys

import webdesk
import tasks

def main(argv):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.DEBUG)
    logging.getLogger('requests.packages.urllib3').propagate = True

    attributes = {'user': argv[1], 'url': argv[2]}
    if not attributes['url'].endswith('/'):
        attributes['url'] += '/'

    tickets = webdesk.get_tickets(attributes)
    tasks_ = tasks.get_tasks()

    import ipdb; ipdb.set_trace()

    #new_tickets = tickets.keys() - tasks_.keys()

    #tw.task_add('test', webdesk_key=ticket['list_params']['key'])

if __name__ == '__main__':
    main(sys.argv)
