import boto3
import logging
from app.boto_factory import BotoFactory


logging.basicConfig(level=logging.INFO)


class VPCOps():
    def __init__(self, account_id):
        self.session = boto3.Session()
        self.account_id = account_id

    def get_all_vpn_connections(self):
        self.vpns = list()
        regions = self.__get_all_regions()
        for r in regions:
            self.vpns += self.__get_vpn_connections(r)
        return self.vpns

    def __get_vpn_connections(self, region):
        ec2 = BotoFactory().get_capability(
            boto3.client, self.session, 'ec2', account_id=self.account_id,
            region=region
            )
        result = ec2.describe_vpn_connections().get('VpnConnections')
        return result

    def get_all_subnets(self):
        self.subnets = list()
        regions = self.__get_all_regions()
        for r in regions:
            self.subnets += self.__get_subnets(r)
        return self.subnets

    def __get_all_regions(self):
        ec2 = self.session.client('ec2')
        regions = set()
        for r in ec2.describe_regions().get('Regions'):
            regions.add(r.get('RegionName'))
        return regions

    def __get_subnets(self, region):
        ec2 = BotoFactory().get_capability(
            boto3.client, self.session, 'ec2', account_id=self.account_id,
            region=region
            )
        pgnt = ec2.get_paginator('describe_subnets')
        itr = pgnt.paginate()
        for i in itr:
            result = i.get('Subnets')
            logging.info(f"{self.account_id}:{region}:{result}")
        return result

    def __paginate(self, method, **kwargs):
        """ example use:
        s3 = session.client('s3')
        for key in __paginate(s3.list_objects_v2, Bucket='bucket'):
            print(key)
        """
        client = method.__self__
        paginator = client.get_paginator(method.__name__)
        for page in paginator.paginate(**kwargs).result_key_iters():
            for result in page:
                yield result
