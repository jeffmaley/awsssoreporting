# awsssoreporting.py

## Description

AWS IAM Identity Center (FKA AWS SSO) connects an IdP to an AWS Organization. Identities are granted access (in the form of Permission Sets) to accounts. The combined identity/permission set/account binding is called an *assignment*. It is challenging to use the AWS Console to generate a report of all granted access. This package provides a way of reporting this access to the terminal or a CSV.

## Usage

awsssoreporting.py \[-a | -u\] -c -f myfile.csv -q
* -a  Report access by AWS account
* -u  Report access by identity
* -c  Write the results to a CSV
* -f  The filename to write the CSV to. Otherwise, the default (aws_sso_reporting-\<date\>.csv) is used
* -q  Quite mode. No results printed to terminal. The default is False.
