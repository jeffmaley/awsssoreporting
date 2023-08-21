# awsssoreporting.py

## Description

AWS IAM Identity Center (FKA AWS SSO) connects an IdP to an AWS Organization. Identities are granted access (in the form of Permission Sets) to accounts. The combined identity/permission set/account binding is called an *assignment*. It is challenging to use the AWS Console to generate a report of all granted access. This package provides a way of reporting this access to the terminal or a CSV.

## Installation

python3 -m pip install boto3
python3 -m pip install awsssoreporting

## Usage

Because this utility uses the AWS IAM Identity Center and Organization APIs, it must be run from the Organization management account.

export AWS_PROFILE=<your AWS profile. This must have read access to the sso-admin, identitystore, and organizations API.>
export AWS_DEFALT_REGION=<region AWS Identity Center is configured in>

awsssoreporting.py \[-a | -u\] -c -f myfile.csv -q
* -a  Report access by AWS account
* -u  Report access by identity
* -c  Write the results to a CSV
* -f  The filename to write the CSV to. Otherwise, the default (aws_sso_reporting-\<date\>.csv) is used
* -q  Quite mode. No results printed to terminal. The default is False.

### TODO
* Support more than one AWS Identity Center Instance
