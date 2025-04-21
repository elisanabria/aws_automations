import json
import boto3
import datetime
import os

# Initialize clients
ec2_client = boto3.client('ec2')
rds_client = boto3.client('rds')


def lambda_handler(event, context):
    # Debug purposes. Prints the whole CloudTrail event
    # print("Received event:", json.dumps(event, indent=2))

    try:
        event_source = event['detail']['eventSource']
        event_name = event['detail']['eventName']
    except KeyError as e:
        print(f"Missing expected key in event: {e}")
        return {'statusCode': 400, 'body': f'Missing key: {str(e)}'}

    resource_id = ''
    resource_type = ''
    account_id = ''
    creds = ''

    # Check if the event is for EC2 or RDS
    if event_source == 'ec2.amazonaws.com' and event_name == 'RunInstances':
        try:
            resource_id = event['detail']['responseElements']['instancesSet']['items'][0]['instanceId']
            resource_type = 'EC2'
        except (KeyError, IndexError) as e:
            print(f"Error extracting instance ID: {e}")
            return {'statusCode': 400, 'body': 'Invalid EC2 event format'}
    elif event_source == 'rds.amazonaws.com' and event_name == 'CreateDBInstance':
        try:
            resource_id = event['detail']['responseElements']['dBInstanceArn']
            resource_type = 'RDS'
        except KeyError as e:
            print(f"Error extracting RDS instance ID: {e}")
            return {'statusCode': 400, 'body': 'Invalid RDS event format'}
    # If neither EC2 nor RDS, skip
    if not resource_id:
        return {'statusCode': 200, 'body': 'No supported resource found'}

    # Initialize clients
    ec2_client = boto3.client('ec2')
    rds_client = boto3.client('rds')

    # Get tags for the resource
    if resource_type == 'EC2':
        tags = event['detail']['responseElements']['instancesSet']['items'][0]['tagSet']['items']
    elif resource_type == 'RDS':
        tags = event['detail']['responseElements']['tagList']

    # Check for 'Ephemeral=True' tag
    ephemeral_tag = next((tag for tag in tags if tag['key'] == 'Ephemeral' and tag['value'] == 'True'), None)

    if ephemeral_tag:
        # Generate the new tags
        user_identity = event['detail']['userIdentity']
        created_by = user_identity.get('userName') or user_identity.get('arn').split('/')[-1]
        created_by_tag = {'Key': 'CreatedBy', 'Value': created_by}
        creation_date_tag = {'Key': 'CreationDate', 'Value': datetime.date.today().isoformat()}

        print(f"CreatedBy: {created_by}")
        print(f"CreationDate: {datetime.date.today().isoformat()}")
        print(f"CreatedBy: {created_by}")

        account_id = event['detail']['recipientAccountId']

        print(f"Account ID: {account_id}")

        print(f"Resource ID: {resource_id}")
        print(f"User: {created_by}")

        sts = boto3.client('sts')            
        assumed_role = sts.assume_role(
            RoleArn=f"arn:aws:iam::{account_id}:role/EphemeralCrossAccountRole",
            RoleSessionName=f"Tagging-Session"
        )
        creds = assumed_role['Credentials']

        # Add the tags to the resource
        if resource_type == 'EC2':
            ec2_client = boto3.client('ec2',
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken']
            )
            ec2_client.create_tags(Resources=[resource_id], Tags=[created_by_tag, creation_date_tag])
        elif resource_type == 'RDS':
            rds_client = boto3.client('rds',
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken']
            )
            rds_client.add_tags_to_resource(ResourceName=resource_id, Tags=[created_by_tag, creation_date_tag])

        return {'statusCode': 200, 'body': f'Tags added to {resource_type} resource: {resource_id}'}
    else:
        return {'statusCode': 200, 'body': f'No Ephemeral tag found for {resource_type} resource: {resource_id}'}
