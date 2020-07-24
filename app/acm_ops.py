import boto3
import logging
from app.boto_factory import BotoFactory


class ACMOps():

    def __init__(self, session, account_id, regions='', certificate_status=''):
        if regions == '':
            regions = set(session.get_available_regions('acm'))
            regions.discard('ap-east-1')    # discard hongkong
            regions.discard('me-south-1')   # discard bahrain
            self.regions = list(regions)
        elif not isinstance(regions, list):
            raise TypeError('Regions must be given in a list')
        else:
            self.regions = regions

        if certificate_status == '':
            self.certificate_status = list()
        elif not isinstance(certificate_status, list):
            raise TypeError("Filters must be in a list: \
                'PENDING_VALIDATION'|'ISSUED'|'INACTIVE'| \
                'EXPIRED'|'VALIDATION_TIMED_OUT'|'REVOKED'|'FAILED'")
        else:
            self.certificate_status = certificate_status

        self.session = session
        self.account_id = account_id
        self.filters = certificate_status

    def get_all_email_validated_certs(self):
        """returns an ARN list of all ACM certificates with email validation"""
        certificates = list()
        for r in self.regions:
            logging.info(f"Processing {self.account_id}:{r}")
            try:
                acm = BotoFactory().get_capability(
                    boto3.client, self.session, 'acm',
                    account_id=self.account_id, region=r, rolename='AxisCloudAdmin'
                )

                pngt = acm.get_paginator('list_certificates')
                itr = pngt.paginate(
                    CertificateStatuses=self.certificate_status
                )
                for i in itr:
                    for c in i.get('CertificateSummaryList'):
                        result = (
                            acm.describe_certificate(
                                CertificateArn=c.get('CertificateArn')
                            )
                        )
                        validations_opts = result.get(
                            'Certificate').get(
                                'DomainValidationOptions')
                        for v in validations_opts:
                            if v.get('ValidationMethod') == 'EMAIL':
                                certificates.append(c.get('CertificateArn'))
            except Exception as e:
                logging.error(f"{e} for {r}")
        logging.info(certificates)
        return certificates
