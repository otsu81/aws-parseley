import boto3
import os
import logging
import json
from app.boto_factory import BotoFactory


class IAMOps():

    def __init__(self, session, account_id):
        self.session = session
        self.account_id = account_id
        self.iam = BotoFactory().get_capability(
            boto3.client, session, 'iam', account_id=account_id)

    def delete_role(self, rolename):
        try:
            # get all policies
            iam_r = BotoFactory().get_capability(
                boto3.resource, self.session, 'iam', self.account_id,
                os.getenv('DEFAULT_ROLE')
            )
            role = iam_r.Role(rolename)

            itr = role.policies.all()
            for i in itr:
                i.delete()

            # delete role
            response = role.delete()
            logging.info(json.dumps(response, indent=4, default=str))

        except iam_r.meta.client.exceptions.NoSuchEntityException as e:
            logging.info(e)
            logging.info(f"{self.account_id}: role {rolename} doesn't exist")

    def remove_idp(self, idp_name):
        saml_arn = f"arn:aws:iam::{self.account_id}:saml-provider/{idp_name}"
        try:
            response = self.iam.delete_saml_provider(
                SAMLProviderArn=saml_arn
            )
            logging.info(json.dumps(response, indent=4, default=str))
        except self.iam.exceptions.NoSuchEntityException:
            logging.info(f"{self.account_id}: IdP {idp_name} doesn't exist")

    def update_assume_role_policy(self, rolename, policy):
        """policy should be in dict-format to be translated to json"""
        try:
            return self.iam.update_assume_role_policy(
                RoleName=rolename,
                PolicyDocument=json.dumps(policy)
            )
        except Exception as e:
            logging.warning(e)

    def list_roles_with_trust(self, trusted_account):
        roles = list()
        pgn = self.iam.get_paginator('list_roles')
        itr = pgn.paginate()
        for i in itr:
            for r in i['Roles']:
                policy_doc = r['AssumeRolePolicyDocument']
                if trusted_account in json.dumps(policy_doc):
                    roles.append((r['Arn']))
        print(roles)
        return roles

    def get_all_iam_users(self):
        users = set()
        pgnt = self.iam.get_paginator('list_users')
        itr = pgnt.paginate()
        for i in itr:
            for user in i['Users']:
                users.add(user['UserName'])
        return users

    def get_all_iam_users_with_pw(self):
        iam_resource = BotoFactory().get_capability(
            boto3.resource, self.session, 'iam', account_id=self.account_id)

        users = self.get_all_iam_users()

        iam_users_with_passwords = set()
        for user in users:
            lp = iam_resource.LoginProfile(user)
            try:
                lp.create_date
                iam_users_with_passwords.add(
                    self.iam.get_user(UserName=user)['User']['UserName']
                )
            except self.iam.exceptions.NoSuchEntityException:
                pass

        return iam_users_with_passwords

    def compare_pw_policy(self, desired_pw_policy):
        """
        Takes IAM current password policy and compares to the desired, return
        map with each discrepancy. desired_pw_policy is in DICT format, see
        boto3 documentation for all options.

        Example desired_pw_policy:

        {
            "MinimumPasswordLength": 16,
            "RequireSymbols": True,
            "RequireNumbers": True,
            "RequireUppercaseCharacters": True,
            "RequireLowercaseCharacters": True,
            "AllowUsersToChangePassword": True,
            "ExpirePasswords": True,
            "MaxPasswordAge": 90,
            "PasswordReusePrevention": 10,
            "HardExpiry": False
        }

        """
        try:
            account_policy = self.iam.get_account_password_policy().get(
                'PasswordPolicy')
            diff_items = {
                k: account_policy[k]
                for k in account_policy if k in desired_pw_policy and
                account_policy[k] != desired_pw_policy[k]
                }
            return diff_items
        except self.iam.exceptions.NoSuchEntityException as e:
            logging.warn(f"No password policy exists. {e}")
            return False

    def set_minimum_pw_policy(self, desired_pw_policy):
        """
        Sets the minimum password policy in the IAM client's AWS account
        If there are stronger password requirements than those in the minimum
        one, the stronger requirement stays
        """
        try:
            account_policy = self.iam.get_account_password_policy().get(
                'PasswordPolicy')
        except self.iam.exceptions.NoSuchEntityException as e:
            logging.warn(
                f"{e}: No password policy exists, setting the desired policy")
            self.iam.update_account_password_policy(**desired_pw_policy)
            return self.iam.get_account_password_policy().get('PasswordPolicy')

        check_if_better = [
            'MinimumPasswordLength',
            'PasswordReusePrevention'
            ]

        for check in check_if_better:
            try:
                if account_policy[check] > desired_pw_policy[check]:
                    desired_pw_policy[check] = account_policy[check]
            except KeyError:
                pass
        self.iam.update_account_password_policy(**desired_pw_policy)
        return(account_policy)

    def add_pw_parameter(self, key, value):
        """
        pushes a specific password policy parameter to the IAM password policy,
        e.g. HardExpiry, MinimumPasswordLength...
        """
        pw_pol = self.iam.get_account_password_policy()['PasswordPolicy']

        try:
            pw_pol[key]
        except KeyError:
            pw_pol[key] = None

        if not pw_pol[key] == value:
            pw_pol[key] = value
            pw_pol.pop('ExpirePasswords')
            self.iam.update_account_password_policy(**pw_pol)
            return f"success"
        else:
            return f"already compliant"
