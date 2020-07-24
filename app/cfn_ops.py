import boto3
import logging
from dotenv import load_dotenv
from app.boto_factory import BotoFactory

load_dotenv
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('parseley')


class CFNOps():
    def __init__(self, account_id):
        self.session = boto3.Session()
        self.account_id = account_id
        self.cfn = BotoFactory().get_capability(
            boto3.client, self.session, 'cloudformation', account_id
        )

    def check_if_stackset_present(self, account_id, stackname):
        paginator = self.cfn.get_paginator('list_stacks')
        itr = paginator.paginate()
        for i in itr:
            for stack in i['StackSummaries']:
                if stackname in stack['StackName'] \
                        and stack['StackStatus'] == 'CREATE_COMPLETE':
                    return True
        return False

    def all_stacks_all_regions(self):
        regions = [
            "eu-north-1",
            "ap-south-1",
            "eu-west-3",
            "eu-west-2",
            "eu-west-1",
            "ap-northeast-2",
            "ap-northeast-1",
            "sa-east-1",
            "ca-central-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "eu-central-1",
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2"
        ]

        stacks_inventory = list()
        for r in regions:
            regional_cfn = BotoFactory().get_capability(
                boto3.client, self.session, 'cloudformation',
                account_id=self.account_id, region=r
            )
            pgnt = regional_cfn.get_paginator('list_stacks')
            itr = pgnt.paginate()
            for i in itr:
                for stack in i['StackSummaries']:
                    log.info(f"{stack['StackId']}:{stack['StackStatus']}")
                    stacks_inventory.append(
                        f"{stack['StackId']}:{stack['StackStatus']}")

        log.info(stacks_inventory)
        return stacks_inventory
