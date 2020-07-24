import boto3
import logging
from app.boto_factory import BotoFactory

logging.basicConfig(level=logging.WARNING)


class CloudtrailOps():
    def get_all_cloudtrails_list(self, session, account_id):
        cloudtrail = BotoFactory().get_capability(
            boto3.client, session, 'cloudtrail', account_id
        )
        trails = cloudtrail.describe_trails(
            includeShadowTrails=True
        ).get('trailList')

        return trails

    def delete_cloudtrail_name(self, session, account_id, region, ct_name):
        cloudtrail = BotoFactory().get_capability(
            boto3.client, session, 'cloudtrail', account_id
        )

        arn = f"arn:aws:cloudtrail:{region}:{account_id}:trail/{ct_name}"
        try:
            print(cloudtrail.delete_trail(Name=arn))
        except Exception as e:
            logging.warning(e)
