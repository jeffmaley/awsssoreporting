"""aws_sso_reporting
This script will return the assigned accounts and permission sets for
users in AWS IAM Identity Center.

It supports the following parameters:
-a - Return assignments and permission sets by account
-u - Return assignments and permission sets by user
-c - Write the output to a CSV
-f - Output file name. The default is aws_sso_reporting.csv.
-q - Quiet mode. No output written to terminal. This is off by default.
"""


import os
import boto3
import botocore
import argparse
import logging
import datetime


logging.basicConfig(level=logging.DEBUG, filename="awsssoreporting.log", format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger()


class Config:
    """Core configuration items
    """
    def __init__(self):
        output_file_append = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H-%M-%S')
        self.CSV_FILENAME = f"aws_sso_reporting{output_file_append}.csv"


class colors:
    """Color specifications for terminal output
    """
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SsoUser:
    """AWS IAM Identity Center users. Stores:
    user's name
    user's ID
    user's groups
    user's assignments
    """
    def __init__(self, name: str = None):
        self.name = name
        self.user_id = None
        self.groups = []
        self.assignments = {}

    def __str__(self):
        return f"Name: {self.name}\nUserId: {self.user_id}\nGroups: {self.groups}\nAssignments: {self.assignments}\n"

    def __repr__(self):
        return f"Name: {self.name}\nUserId: {self.user_id}\nGroups: {self.groups}\nAssignments: {self.assignments}\n"

    def get_name(self):
        return self.name

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def add_group(self, group_id):
        self.groups.append(group_id)

    def get_groups(self):
        return self.groups

    def add_assignment(self, account_id, permission_set, group_name=None):
        try:
            self.assignments[account_id].update({permission_set: group_name})
        except KeyError:
            self.assignments.update({account_id: {permission_set: group_name}})

    def get_assignments(self):
        for account_id, details in self.assignments.items():
            yield account_id, details


class AwsAccount:
    """AWS accounts. Stores:
    account Id
    assignments by group with user list and by user
    """
    def __init__(self, account_id):
        self.account_id = account_id
        # The assignments dict is overly-complicated.
        # {permission_set_name: {group: group_name}}
        # {permission_set_name: {user: user_name}}
        # {permission_set_name: {group: group_name, users: [user_name, user_name, user_name]}}
        self.assignments = {}

    def __str__(self):
        return f"Account Id: {self.account_id}"

    def __repr__(self):
        return f"Account Id: {self.account_id}"

    def get_account_id(self):
        return self.account_id

    def add_assignment(self, permission_set_name, user_name=None, group_name=None):
        try:
            if user_name and not group_name:
                self.assignments[permission_set_name].update({"user": user_name})
            else:
                self.assignments[permission_set_name].update({"group": group_name, "users": user_name})
        except KeyError:
            if user_name and not group_name:
                self.assignments.update({permission_set_name: {"user": user_name}})
            else:
                self.assignments.update({permission_set_name: {"group": group_name, "users": user_name}})

    def get_assignments(self):
        for permission_set_name, details in self.assignments.items():
            yield permission_set_name, details


def list_instances(sso_client: botocore.client) -> str:
    """Returns the configured IAM Identity Center instances.
    returns the Identity Store ID and Instance ID
    """
    response = sso_client.list_instances(  # TODO support more than 1
        MaxResults=1
    )
    return response.get("Instances")[0].get("InstanceArn"), response.get("Instances")[0].get("IdentityStoreId")


def list_accounts(org_client: botocore.client) -> str:
    response = org_client.list_accounts()
    for account in response.get("Accounts"):
        yield account.get("Id")


def list_account_assignments(sso_client: botocore.client, instance_arn: str, account_id: str, permission_set_arn: str) -> dict:
    response = sso_client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn
    )
    for account_assignment in response.get("AccountAssignments"):
        yield account_assignment


def list_permission_sets_provisioned_to_account(sso_client: botocore.client, instance_arn: str, account_id: str) -> str:
    response = sso_client.list_permission_sets_provisioned_to_account(
        InstanceArn=instance_arn,
        AccountId=account_id
    )
    for permission_set in response.get("PermissionSets"):
        yield permission_set


def describe_identity(identity_store_client: botocore.client, identity_store_id: str, identity_id: str, identity_type: str) -> str:
    if identity_type == "USER":
        return describe_user(identity_store_client, identity_store_id, identity_id)
    elif identity_type == "GROUP":
        return describe_group(identity_store_client, identity_store_id, identity_id)
    else:
        print("identity_type must be USER or GROUP")
        return None


def describe_group(identity_store_client: botocore.client, identity_store_id: str, user_id: str) -> str:
    response = identity_store_client.describe_group(
        IdentityStoreId=identity_store_id,
        GroupId=user_id
    )
    return response.get("DisplayName")


def describe_user(identity_store_client: botocore.client, identity_store_id: str, user_id: str) -> str:
    response = identity_store_client.describe_user(
        IdentityStoreId=identity_store_id,
        UserId=user_id
    )
    return response.get("UserName")


def list_group_memberships(identity_store_client: botocore.client, identity_store_id: str, group_id: str, users: dict = None) -> dict:
    response = identity_store_client.list_group_memberships(
        IdentityStoreId=identity_store_id,
        GroupId=group_id
    )
    for group_membership in response.get("GroupMemberships"):
        yield describe_user(identity_store_client, identity_store_id, group_membership.get("MemberId").get("UserId")), group_membership.get("MemberId").get("UserId")


def describe_permission_set(sso_client: botocore.client, instance_arn: str, permission_set_arn: str) -> str:
    response = sso_client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response.get("PermissionSet").get("Name")


def list_users(identity_store_client: botocore.client, identity_store_id) -> dict:
    response = identity_store_client.list_users(
        IdentityStoreId=identity_store_id
    )
    users = {}
    for user in response.get("Users"):
        user_obj = SsoUser(name=user.get("UserName"))
        user_obj.set_user_id(user.get("UserId"))
        users.update({user_obj.get_user_id(): user_obj})
    return users


def list_groups(identity_store_client: botocore.client, identity_store_id: str, users: dict) -> str:
    response = identity_store_client.list_groups(
        IdentityStoreId=identity_store_id
    )
    for group in response.get("Groups"):
        for x, user_id in list_group_memberships(identity_store_client, identity_store_id, group.get("GroupId")):
            users[user_id].add_group(group.get("GroupId"))


def write_console(args, content_obj) -> None:
    if args.by_account:
        print(f"{colors.YELLOW}{colors.BOLD}{content_obj.get_account_id()}{colors.ENDC}")
        for permission_set_name, details in content_obj.get_assignments():
            print(f"\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
            if isinstance(details, dict) and details.get("group"):
                print(f"\t\t{details.get('group')}")
                if details.get("users"):
                    for user_name in details.get("users"):
                        print(f"\t\t\t{colors.GREEN}{user_name}{colors.ENDC}")
            elif isinstance(details, dict) and details.get("user"):
                print(f"\t\t{colors.GREEN}{details.get('user')}{colors.ENDC}")
    if args.by_user:
        print(f"{colors.GREEN}{colors.BOLD}{content_obj.get_name()}{colors.ENDC}")
        print("\tAssignments")
        for account_id, details in content_obj.get_assignments():
            print(f"\t\t{colors.YELLOW}{account_id}{colors.ENDC}")
            for permission_set_name, group_name in details.items():
                if not group_name:
                    print(f"\t\t\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
                else:
                    print(f"\t\t\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
                    print(f"\t\t\t\t{group_name}")
    return


def write_csv(args, filename, content_objs) -> None:
    with open(filename, "w") as f:
        if args.by_account:
            f.write("AccountId, Permission Set Name, User or Group, Members\n")
            for _, aws_account in content_objs.items():
                for permission_set_name, details in aws_account.get_assignments():
                    if isinstance(details, dict) and details.get("group"):
                        if details.get("users"):
                            for user_name in details.get("users"):
                                f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('group')},{user_name}\n")
                        else:
                            f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('group')}\n")
                    elif isinstance(details, dict) and details.get("user"):
                        f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('user')}\n")
        if args.by_user:
            f.write("User, AccountId, Permission Set Name, Group Name\n")
            for _, user in content_objs.items():
                for account_id, details in user.get_assignments():
                    for permission_set_name, group_name in details.items():
                        if not group_name:
                            f.write(f"{user.get_name()},{account_id},{permission_set_name}\n")
                        else:
                            f.write(f"{user.get_name()},{account_id},{permission_set_name},{group_name}\n")
    return


def main(args):
    if args.by_user and args.by_account:
        logger.error("Parameter error: cannot specify both by_user and by_account")
        print("Parameter error: cannot specify both by_user and by_account")
        exit(1)

    if not args.by_user and not args.by_account:
        print("Please select either -by_user or by_account")
        exit(1)

    config = Config()

    try:
        aws_region = os.environ["AWS_DEFAULT_REGION"]
    except KeyError:
        logger.error("Please set AWS_DEFAULT_REGION with the region AWS IAM Identity Center is configured in.")
        print("Please set AWS_DEFAULT_REGION with the region AWS IAM Identity Center is configured in.")
        exit(1)
    try:
        aws_profile = os.environ["AWS_PROFILE"]
    except KeyError:
        logger.info("Using the default AWS profile")
        print("Using the default AWS profile")
        aws_profile=None
    boto3_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    sso_client = boto3_session.client("sso-admin", region_name=aws_region)
    identity_store_client = boto3_session.client("identitystore", region_name=aws_region)
    org_client = boto3_session.client("organizations", region_name=aws_region)

    instance_arn, identity_store_id = list_instances(sso_client)
    users = list_users(identity_store_client, identity_store_id)
    list_groups(identity_store_client, identity_store_id, users)

    if args.by_user:
        for account_id in list_accounts(org_client):
            for permission_set_arn in list_permission_sets_provisioned_to_account(sso_client, instance_arn, account_id):
                permission_set_name = describe_permission_set(sso_client, instance_arn, permission_set_arn)
                for account_assignment in list_account_assignments(sso_client, instance_arn, account_id, permission_set_arn):
                    for user_id, _ in users.items():
                        if account_assignment.get("PrincipalType") == "USER":
                            users[user_id].add_assignment(account_id, permission_set_name)
                        elif account_assignment.get("PrincipalType") == "GROUP":
                            user_groups = users[user_id].get_groups()
                            if account_assignment.get("PrincipalId") in user_groups:
                                group_name = describe_identity(identity_store_client, identity_store_id, account_assignment.get("PrincipalId"), account_assignment.get("PrincipalType"))
                                users[user_id].add_assignment(account_id, permission_set_name, group_name)
        if not args.quiet_mode:
            for _, user in users.items():
                write_console(args, user)
        if args.csv:
            if args.output_file:
                output_file = args.output_file
            else:
                output_file = config.CSV_FILENAME
            write_csv(args, output_file, users)
    if args.by_account:
        aws_accounts = {}
        for account_id in list_accounts(org_client):
            aws_account = AwsAccount(account_id)
            for permission_set_arn in list_permission_sets_provisioned_to_account(sso_client, instance_arn, account_id):
                permission_set_name = describe_permission_set(sso_client, instance_arn, permission_set_arn)
                for account_assignment in list_account_assignments(sso_client, instance_arn, account_id, permission_set_arn):
                    name = describe_identity(identity_store_client, identity_store_id, account_assignment.get("PrincipalId"), account_assignment.get("PrincipalType"))
                    if account_assignment.get("PrincipalType") == "GROUP":
                        group_members = []
                        for user, _ in list_group_memberships(identity_store_client, identity_store_id, account_assignment.get("PrincipalId")):
                            group_members.append(user)
                        aws_account.add_assignment(permission_set_name, group_name=name, user_name=group_members)
                    elif account_assignment.get("PrincipalType") == "USER":
                        aws_account.add_assignment(permission_set_name, user_name=name)
            aws_accounts.update({account_id: aws_account})
        if not args.quiet_mode:
            for aws_account_id, aws_account in aws_accounts.items():
                write_console(args, aws_account)
        if args.csv:
            if args.output_file:
                output_file = args.output_file
            else:
                output_file = config.CSV_FILENAME
            write_csv(args, output_file, aws_accounts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--by_account", action="store_true")
    parser.add_argument("-u", "--by_user", action="store_true")
    parser.add_argument("-c", "--csv", action="store_true")
    parser.add_argument("-f", "--output_file")
    parser.add_argument("-q", "--quiet_mode", action="store_true", default=False)
    args = parser.parse_args()
    main(args)
