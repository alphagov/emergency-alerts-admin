import os

from app.utils.user import _email_address_ends_with

with open("{}/email_domains_blocked.txt".format(os.path.dirname(os.path.realpath(__file__)))) as email_domains_blocked:
    EMAIL_DOMAIN_BLOCKED_NAMES = [line.strip() for line in email_domains_blocked]


def is_blocked_email_domain(email_address):
    return _email_address_ends_with(email_address, EMAIL_DOMAIN_BLOCKED_NAMES)
