import boto3
import logging
import os
from app.boto_factory import BotoFactory

log = logging.getLogger('parseley')
log.setLevel(os.environ.get('LOGLEVEL'))


class OrganizationsOps():

    def __init__(self, session):
        if os.environ.get('OU_BLOCKLIST'):
            self.blocklist = os.environ.get('OU_BLOCKLIST').split(',')
            log.info(f"OU blocklist: {self.blocklist}")
        else:
            log.warn(
                "No OU_BLOCKLIST present in ENV, all OUs can be traversed"
            )
            self.blocklist = set()

        self.org = BotoFactory().get_capability(
            boto3.client, session, 'organizations'
        )

    def get_all_children_ou(self, parent_ou):
        ous = set()
        log.info(f"Getting children OU for {parent_ou}")
        pgnt = self.org.get_paginator('list_organizational_units_for_parent')
        itr = pgnt.paginate(
            ParentId=parent_ou
        )

        for i in itr:
            for ou in i['OrganizationalUnits']:
                if ou['Id'] not in self.blocklist:
                    ous.add(ou['Id'])

        if ous:
            for ou in ous.copy():
                ous.update(self.get_all_children_ou(ou))

        return ous

    def get_active_accounts_from_ous(self, ous):
        pngt = self.org.get_paginator('list_accounts_for_parent')
        accounts = list()
        for ou in ous:
            log.info(f"Getting accounts from {ou}")
            accounts.extend(
                [account['Id'] for account in pngt.paginate(
                    ParentId=ou
                ).build_full_result()['Accounts'] if
                    account['Status'] == 'ACTIVE']
            )
        return accounts

    def get_accounts_from_root(self):
        root_ou = self.org.list_roots()['Roots'][0]['Id']
        return self.get_active_accounts_from_ous(
            self.get_all_children_ou(root_ou)
        )
