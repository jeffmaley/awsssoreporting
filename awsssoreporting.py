import boto3
import botocore
import argparse

class Config:
    def __init__(self):
        self.INSTANCE_ARN = "arn:aws:sso:::instance/ssoins-72233303c01c6b87"
        self.IDENTITY_STORE_ID = "d-9067628181"
        self.CSV_FILENAME = "aws_sso_reporting.csv"


class colors:
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
    def __init__(self, name: str=None):
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
        for account_id,details in self.assignments.items():
            yield account_id,details


class AwsAccount:
    def __init__(self, account_id):
        self.account_id = account_id
        # {permission_set_name: {group: group_name}}
        # {permission_set_name: {user: user_name}}
        # {permission_set_name: {group: group_name, users: [user_name, user_name, user_name]}}
        self.assignments = {}

    def get_account_id(self):
        return self.account_id

    def add_assignment(self, permission_set_name, user_name=None, group_name=None):
        try:
            if user_name and not group_name:
                self.assignments[permission_set_name].update({"user": user_name})
            elif group_name and not user_name:
                self.assignments[permission_set_name].update({"group": group_name, "users": user_name})
            #else:
            #    self.assignments[permission_set_name].update({group_name: user_name})
        except KeyError:
            if user_name and not group_name:
                self.assignments.update({permission_set_name: {"user": user_name}})
            elif group_name and not user_name:
                self.assignments.update({permission_set_name: {"group": group_name, "users": user_name}})
            #else:
            #    self.assignments.update({permission_set_name: {group_name: user_name}})

    def get_assignments(self):
        for permission_set_name,details in self.assignments.items():
            yield permission_set_name,details


def list_accounts(org_client):
    response = org_client.list_accounts()
    for account in response.get("Accounts"):
        yield account.get("Id")


def list_permission_sets(sso_client, instance_arn=None):
    permission_sets = []
    response = sso_client.list_permission_sets(
        InstanceArn=instance_arn
    )
    for i in response.get("PermissionSets"):
        permission_sets.append(i)
    next_token = response.get("NextToken")
    while next_token:
        response = sso_client.list_permission_sets(
            InstanceArn=instance_arn,
            NextToken=next_token
        )
        for i in response.get("PermissionSets"):
            permission_sets.append(i)
        next_token = response.get("NextToken")
    return permission_sets


def list_account_assignments(sso_client: botocore.client, instance_arn: str=None, account_id: str=None, permission_set_arn: str=None):
    client = boto3.client("sso-admin", region_name="us-east-1")
    response = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn
    )
    for account_assignment in response.get("AccountAssignments"):
        yield account_assignment


def list_accounts_for_provisioned_permission_set(sso_client, instance_arn=None, permission_set_arn=None):
    client = boto3.client("sso-admin", region_name="us-east-1")
    response = client.list_accounts_for_provisioned_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    print(response)


def list_permission_sets_provisioned_to_account(sso_client: botocore.client, instance_arn: str=None, account_id: str=None):
    response = sso_client.list_permission_sets_provisioned_to_account(
        InstanceArn=instance_arn,
        AccountId=account_id
    )
    #print(response)
    for permission_set in response.get("PermissionSets"):
        yield permission_set


def get_user_id():
    client = boto3.client("identitystore", region_name="us-east-1")
    response = client.get_user_id(
        IdentityStoreId="d-9067628181",
        AlternateIdentifier={
            'UniqueAttribute': {
                'AttributePath': 'userName',
                'AttributeValue': 'mrplaydoh@gmail.com'
            }
        }
    )
    print(response)

def describe_identity(identity_store_client: botocore.client, identity_store_id: str, identity_id: str, identity_type: str):
    if identity_type == "USER":
        return describe_user(identity_store_client, identity_store_id, identity_id)
    elif identity_type == "GROUP":
        return describe_group(identity_store_client, identity_store_id, identity_id)
    else:
        print("identity_type must be USER or GROUP")
        return None


def describe_group(identity_store_client: botocore.client, identity_store_id: str, user_id: str):
    response = identity_store_client.describe_group(
        IdentityStoreId=identity_store_id,
        GroupId=user_id
    )
    return response.get("DisplayName")


def describe_user(identity_store_client: botocore.client, identity_store_id: str, user_id: str):
    response = identity_store_client.describe_user(
        IdentityStoreId=identity_store_id,
        UserId=user_id
    )
    return response.get("UserName")

def list_group_memberships(identity_store_client: botocore.client, identity_store_id: str, group_id: str, users: dict=None):
    response = identity_store_client.list_group_memberships(
        IdentityStoreId=identity_store_id,
        GroupId=group_id
    )
    for group_membership in response.get("GroupMemberships"):
        yield describe_user(identity_store_client, identity_store_id, group_membership.get("MemberId").get("UserId")), group_membership.get("MemberId").get("UserId")


def describe_permission_set(sso_client: botocore.client, instance_arn: str, permission_set_arn: str):
    response = sso_client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response.get("PermissionSet").get("Name")


def list_users(identity_store_client: botocore.client, identity_store_id):
    response = identity_store_client.list_users(
        IdentityStoreId=identity_store_id
    )
    users = {}
    for user in response.get("Users"):
        user_obj = SsoUser(name=user.get("UserName"))
        user_obj.set_user_id(user.get("UserId"))
        users.update({user_obj.get_user_id(): user_obj})
    return users


def list_groups(identity_store_client: botocore.client, identity_store_id: str, users: dict):
    response = identity_store_client.list_groups(
        IdentityStoreId=identity_store_id
    )
    for group in response.get("Groups"):
        for x,user_id in list_group_memberships(identity_store_client, identity_store_id, group.get("GroupId")):
            users[user_id].add_group(group.get("GroupId"))


def write_console(args, content_obj):
    if args.by_account:
        print(f"{colors.YELLOW}{colors.BOLD}{content_obj.get_account_id()}{colors.ENDC}")
        for permission_set_name,details in content_obj.get_assignments():
            print(f"\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
            if isinstance(details, dict) and details.get("group"):
                print(f"\t\t{details.get('group')}")
                if details.get("users"):
                    for user_name in details.get("users"):
                        print(f"\t\t\t{colors.GREEN}{user_user}{colors.ENDC}")
            elif isinstance(details, dict) and details.get("user"):
                print(f"\t\t{colors.GREEN}{details.get('user')}{colors.ENDC}")
    if args.by_user:
        print(f"{colors.GREEN}{colors.BOLD}{content_obj.get_name()}{colors.ENDC}")
        print(f"\tAssignments")
        for account_id,details in content_obj.get_assignments():
            print(f"\t\t{colors.YELLOW}{account_id}{colors.ENDC}")
            for permission_set_name,group_name in details.items():
                if not group_name:
                    print(f"\t\t\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
                else:
                    print(f"\t\t\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
                    print(f"\t\t\t\t{group_name}")
    return


def write_csv(args, filename, content_objs):
    with open(filename, "w") as f:
        if args.by_account:
            f.write("AccountId, Permission Set Name, User or Group, Members\n") 
            for _,aws_account in content_objs.items():
                #output = f"{aws_account.get_account_id()}"
                for permission_set_name,details in aws_account.get_assignments():
                    #output = f"{output},{permission_set_name}"
                    if isinstance(details, dict) and details.get("group"):
                        #output = f"{output},{details.get('group')}"
                        if details.get("users"):
                            for user_name in details.get("users"):
                                #output = f"{output},{details.get('users')}\n"
                                f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('group')},{details.get('users')}\n")
                        else:
                            #output = f"{output}\n"
                            f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('group')}\n")
                    elif isinstance(details, dict) and details.get("user"):
                        f.write(f"{aws_account.get_account_id()},{permission_set_name},{details.get('user')}\n")
                        #output = f"{output},{details.get('user')}\n"
        if args.by_user:
            f.write("User, AccountId, Permission Set Name, Group Name\n")
            for _,user in content_objs.items():
                for account_id,details in user.get_assignments():
                    for permission_set_name,group_name in details.items():
                        if not group_name:
                            f.write(f"{user.get_name()},{account_id},{permission_set_name}\n")
                        else:
                            f.write(f"{user.get_name()},{account_id},{permission_set_name},{group_name}\n")
    return

def main(args):
    config = Config()
    sso_client = boto3.client("sso-admin", region_name="us-east-1")
    identity_store_client = boto3.client("identitystore", region_name="us-east-1")
    #list_account_assignments(sso_client, instance_arn=config.INSTANCE_ARN)
    org_client = boto3.client("organizations", region_name="us-east-1")
    #list_accounts_for_provisioned_permission_set(sso_client, instance_arn=config.INSTANCE_ARN)
    #permission_sets = list_permission_sets_provisioned_to_account(sso_client, instance_arn=config.INSTANCE_ARN, account_id="448798155788")
    users = list_users(identity_store_client, config.IDENTITY_STORE_ID)
    list_groups(identity_store_client, config.IDENTITY_STORE_ID, users)
    if args.by_user:
        for account_id in list_accounts(org_client):
            for permission_set in list_permission_sets_provisioned_to_account(sso_client, instance_arn=config.INSTANCE_ARN, account_id=account_id):
                permission_set_name = describe_permission_set(sso_client, config.INSTANCE_ARN, permission_set)
                for account_assignment in list_account_assignments(sso_client, instance_arn=config.INSTANCE_ARN, account_id="448798155788",permission_set_arn=permission_set):
                    for user_id,user in users.items():
                        if account_assignment.get("PrincipalType") == "USER":
                            users[user_id].add_assignment(account_id, permission_set_name)
                        elif account_assignment.get("PrincipalType") == "GROUP":
                            user_groups = users[user_id].get_groups()
                            if account_assignment.get("PrincipalId") in user_groups:
                                group_name = describe_identity(identity_store_client, config.IDENTITY_STORE_ID, account_assignment.get("PrincipalId"), account_assignment.get("PrincipalType"))
                                users[user_id].add_assignment(account_id, permission_set_name, group_name)
        for user_id,user in users.items():
            write_console(args, user)
        #    print(f"{colors.GREEN}{colors.BOLD}{user.get_name()}{colors.ENDC}")
        #    print(f"\tAssignments")
        #    for account_id,details in user.get_assignments():
        #        print(f"\t\t{colors.YELLOW}{account_id}{colors.ENDC}")
        #        for permission_set_name,group_name in details.items():
        #            if not group_name:
        #                print(f"\t\t\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
        #            else:
        #                print(f"\t\t\t{colors.CYAN}{permission_set_name} - {colors.ENDC}{group_name}")
        write_csv(args, config.CSV_FILENAME, users)
    if args.by_account:
        aws_accounts = {}
        for account_id in list_accounts(org_client):
            aws_account = AwsAccount(account_id)
            #print(f"{colors.YELLOW}{colors.BOLD}{account_id}{colors.ENDC}")
            for permission_set in list_permission_sets_provisioned_to_account(sso_client, instance_arn=config.INSTANCE_ARN, account_id=account_id):
                permission_set_name = describe_permission_set(sso_client, config.INSTANCE_ARN, permission_set)
                #print(f"\t{colors.CYAN}{permission_set_name}{colors.ENDC}")
                for account_assignment in list_account_assignments(sso_client, instance_arn=config.INSTANCE_ARN, account_id="448798155788",permission_set_arn=permission_set):
                    name = describe_identity(identity_store_client, config.IDENTITY_STORE_ID, account_assignment.get("PrincipalId"), account_assignment.get("PrincipalType"))
                    if account_assignment.get("PrincipalType") == "GROUP":
                        #print(f"\t\t{name}")
                        group_members = []
                        for user,x in list_group_memberships(identity_store_client, config.IDENTITY_STORE_ID,account_assignment.get("PrincipalId")):
                            #print(f"\t\t\t{colors.GREEN}{user}{colors.ENDC}")
                            group_members.append(user)
                        aws_account.add_assignment(permission_set_name, group_name=name, user_name=group_members)
                    elif account_assignment.get("PrincipalType") == "USER":
                        #print(f"\t\t{colors.GREEN}{name}{colors.ENDC}")
                        aws_account.add_assignment(permission_set_name, user_name=name)
            aws_accounts.update({account_id: aws_account})
        for aws_account_id,aws_account in aws_accounts.items():
            write_console(args, aws_account)
        write_csv(args, config.CSV_FILENAME, aws_accounts)
    #get_user_id()
    #print(users)
    #print(users)
    #list_group_memberships(identity_store_client, config.IDENTITY_STORE_ID,,users)
    #list_groups(identity_store_client, config.IDENTITY_STORE_ID, users)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--by_account", action="store_true")
    parser.add_argument("-u", "--by_user", action="store_true")
    args = parser.parse_args()
    main(args)
