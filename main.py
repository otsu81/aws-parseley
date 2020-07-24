import boto3
import logging
import json
import os
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from app.boto_factory import BotoFactory
from app.cfn_ops import CFNOps
from app.cloudtrail_ops import CloudtrailOps
from app.iam_ops import IAMOps
from app.r53_ops import Route53Ops
from app.acm_ops import ACMOps
from app.vpc_ops import VPCOps
from app.org_ops import OrganizationsOps

load_dotenv()

# set up logging to file - see previous section for more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%y-%m-%d %H:%M',
    filename=f"log/{datetime.now()}.log",
    filemode='w'
    )
log = logging.getLogger('parseley')
# log.addHandler(logging.StreamHandler())

account_list = list()
MAX_THREADS = 20
SESSION_INFO = {
    # 'profile_name': os.getenv('DEFAULT_CLI_PROFILE'),
    'region_name': os.getenv('DEFAULT_REGION')
}

arn_list = list()
hosted_zone_dict = dict()
cloudtrails_dict = dict()
subnets = list()
vpns = list()
pw_policy_inventory = dict()


def __json_print(inp):
    print(json.dumps(inp, indent=4, default=str))


def __write_csv(filename, fieldnames, input_list):
    """expects a list of dicts"""
    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in input_list:
            writer.writerow(i)


def get_active_accounts(session):
    """
    Fetches all active account IDs from an Organization. To get accounts from
    an OU structure, refer to OrganizationsOps class instead, app/org_ops.py
    """
    org = BotoFactory().get_capability(
        boto3.client, session, 'organizations', os.getenv('ORG_ACCOUNT'),
        os.getenv('DEFAULT_ROLE')
    )
    accounts = dict()
    paginator = org.get_paginator('list_accounts')
    itr = paginator.paginate()
    for i in itr:
        for account in i['Accounts']:
            if account['Status'] == 'ACTIVE':
                accounts[account['Id']] = account
    return accounts


def fetch_role_arn(session, account_id, rolename):
    global arn_list
    iam = BotoFactory().get_capability(
        boto3.resource, session, 'iam', account_id=account_id
    )
    try:
        role = iam.Role(rolename)
        print(role.arn)
        arn_list.append(role.arn)
    except iam.meta.client.exceptions.NoSuchEntityException as e:
        log.warn(f"not found in {account_id}, {e}")


def fetch_roles_with_trust(session, account_id, trusted_account_id):
    global arn_list
    arns = IAMOps(session, account_id).list_roles_with_trust(
        trusted_account_id)
    arn_list += arns


def delete_role_from_arn(session, arn):
    # must have official full ARN for role, e.g.
    # arn:aws:iam::123456789012:role/OrganizationAccountAccessRole
    print(f"Deleting {arn}")
    account_id = arn[13:25]
    rolename = arn[31:]
    IAMOps(session, account_id).delete_role(rolename)


def set_minimum_pw_policy(session, account_id):
    desired_pw_policy = {
        "MinimumPasswordLength": 16,
        "RequireNumbers": True,
        "RequireUppercaseCharacters": True,
        "RequireLowercaseCharacters": True,
        "AllowUsersToChangePassword": True,
        "MaxPasswordAge": 90,
        "PasswordReusePrevention": 10,
        "HardExpiry": True
    }
    log.info(IAMOps(session, account_id).set_minimum_pw_policy(
        desired_pw_policy
    ))


def get_iam_pw_policy_inventory(session, account_id):
    global pw_policy_inventory
    iam_ops = IAMOps(session, account_id)
    desired_policy = {
            "MinimumPasswordLength": 16,
            "RequireNumbers": True,
            "RequireUppercaseCharacters": True,
            "RequireLowercaseCharacters": True,
            "AllowUsersToChangePassword": True,
            "ExpirePasswords": True,
            "MaxPasswordAge": 90,
            "PasswordReusePrevention": 10,
            "HardExpiry": True
    }
    pw_policy_inventory[account_id] = iam_ops.compare_pw_policy(desired_policy)


def add_console_users_to_group(session, account_id, group_name):
    """
    adds all users with password (login profile) active to a specified group
    """
    users_w_pw = IAMOps().get_all_iam_users_with_pw(session, account_id)
    iam = BotoFactory().get_capability(
        boto3.client, session, 'iam', account_id=account_id
    )
    for user in users_w_pw:
        iam.add_user_to_group(
            GroupName='RequireMFA',
            UserName=user
        )
        log.info(f"Added {account_id}:{user} to {group_name}")
        print(f"Added {account_id}:{user} to {group_name}")


def get_all_hosted_zones(session, account_id):
    """
    get all HZ from a given account
    """
    global hosted_zone_dict
    r53_client = BotoFactory().get_capability(
        boto3.client, session, 'route53', account_id=account_id
    )
    hz = Route53Ops(client=r53_client).get_all_hosted_zones()
    log.info(f"{account_id}: {hz}")
    print(f"{account_id}: {hz}")
    if len(hz) > 0:
        hosted_zone_dict[account_id] = hz


def get_all_cloudtrails(session, account_id):
    """get all cloudtrails from an account"""
    global cloudtrails_dict
    cloudtrails_dict[account_id] = CloudtrailOps().get_all_cloudtrails_list(
        session, account_id)


def delete_cloudtrail(session, account_id, region, ct_name):
    "delete a specific cloudtrail from an account"
    CloudtrailOps().delete_cloudtrail_name(
        session, account_id, region, ct_name
    )


def get_all_iam_users(session, account_id):
    return IAMOps(session, account_id).get_all_iam_users()


def get_acm_email_validations(session, account_id, certificate_statuses):
    acm = ACMOps(session, account_id, certificate_status=certificate_statuses)
    arn_list.extend(acm.get_all_email_validated_certs())


def get_all_subnets_all_regions(session, account_id):
    global subnets
    result = VPCOps(session, account_id).get_all_subnets()
    __json_print(result)
    subnets += result


def get_all_vpn_connections_all_regions(account_id):
    global vpns
    result = VPCOps(account_id).get_all_vpn_connections()
    if result is not None:
        for r in result:
            r['OwnerId'] = account_id
        vpns += result
        __json_print(result)


def cloudformation_inventory_all_regions(account_id):
    global arn_list
    cfn = CFNOps(account_id)
    arn_list.extend(cfn.all_stacks_all_regions())


# --------------------------------------------------------------
def main():

    session = boto3.Session(**SESSION_INFO)
    accounts = OrganizationsOps(session).get_accounts_from_root()

    """use this for non-threaded testing since ThreadPoolExecutor is wonky
    with exceptions"""
    # for account in account_set:
    #     print(f"Processing account {account}")
    #     get_all_vpn_connections_all_regions(account)

    """run ThreadPoolExecutor"""
    futures = dict()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for account in accounts:
            log.info(f"Processing account {account}")
            futures[account] = executor.submit(
                cloudformation_inventory_all_regions, account
            )

    for a in futures:
        try:
            futures[a].result()
        except Exception as e:
            print(f"Exception {a}: {str(e)}")

    global arn_list
    with open('out/cfn_inventory.txt', 'w') as f:
        for a in arn_list:
            f.write(f"{a}\n")


if __name__ == '__main__':
    main()
