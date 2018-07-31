import gi

gi.require_version('Secret', '1')

from gi.repository import Secret

SCHEMA = Secret.Schema.new(
    'uk.org.robots.WebDesk',
    Secret.SchemaFlags.NONE,
    {
        'user': Secret.SchemaAttributeType.STRING,
        'url': Secret.SchemaAttributeType.STRING,
    }
)

def get_password(attributes):
    password = Secret.password_lookup_sync(SCHEMA, attributes, None)
    if password is None:
        from getpass import getpass
        password = getpass('Password for \'{user}\' @ <{url}>:'.format(**attributes))
    Secret.password_store_sync(SCHEMA, attributes, Secret.COLLECTION_DEFAULT, 'WebDesk for \'{user}\' @ <{url}?'.format(**attributes), password, None)
    return password
