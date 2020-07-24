import logging


class Route53Ops():
    """
    Class for running Route 53 specific operations
    """

    def __init__(self, client=''):
        if client == '':
            raise AttributeError('No Route53 client specified')
        self.route53cl = client

    def get_all_hosted_zones(self):
        hosted_zones_list = list()
        pgnt = self.route53cl.get_paginator('list_hosted_zones')
        itr = pgnt.paginate()
        for i in itr:
            for z in i.get('HostedZones'):
                logging.info(f"{z.get('Id')}:{z.get('Name')}")
                hosted_zones_list.append(str(z.get('Name')))
        return hosted_zones_list
