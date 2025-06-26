import boto3
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sns = boto3.client('sns')

SINGLE_LINE_LENGTH = 80
DOUBLE_LINE_LENGTH = 47

HEADER_TEXT = 'New CloudTrail Alert\n'

# this function will add a horizontal line to the email
def add_horizontal_line(text_body, line_char, line_length):
    y = 0
    while y <= line_length:
        text_body += line_char
        y += 1
    text_body += '\n'
    
    return text_body

def lambda_handler(event, context):
    
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
    IAM_Events = ['CreateRole', 'DeleteRole', 'AddUserToRole', 'DeleteRolePolicy', 'DeleteUserPolicy', 'PutGroupPolicy', 'PutRolePolicy', 'PutUserPolicy', 'CreatePolicy', 'DeletePolicy', 'CreatePolicyVersion', 'DeletePolicyVersion', 'AttachRolePolicy', 'DetachRolePolicy', 'AttachUserPolicy', 'DetachUserPolicy', 'AttachGroupPolicy', 'DetachGroupPolicy', 'AddUsersToGroup', 'UpdateAssumeRolePolicy']
    SourceIP_Excluded = ['ssm.amazonaws.com', 'sso.amazonaws.com']
    send_alert_IAM = True
    send_alert_others = True

    try:
        # Extract the CloudTrail event detail
        detail = event.get('detail', {})

        # Extract relevant fields
        event_name = detail.get('eventName')
        event_source = detail.get('eventSource')
        user_identity = detail.get('userIdentity', {})
        account_id = detail.get('recipientAccountId') or user_identity.get('accountId')
        user_type = user_identity.get('type')
        user = user_identity.get('userName') or user_identity.get('principalId')
        source_ip = detail.get('sourceIPAddress')
        time = detail.get('eventTime')
        region = detail.get('awsRegion')
        request_params = detail.get('requestParameters')
        resources = detail.get('resources', [])

        send_alert_IAM = event_name in IAM_Events and source_ip not in SourceIP_Excluded
        send_alert_others = event_name not in IAM_Events
        
        # Format email content
        subject = f"New CloudTrail Alert: {event_name} in {account_id}"
        message = f"""
    🔔 CloudTrail Alert Triggered

        📌 Event: {event_name}
        📌 Source: {event_source}
        📌 Account ID: {account_id}
        📌 Region: {region}
        👤 User Type: {user_type}
        👤 User: {user}
        🌍 Source IP: {source_ip}
        🕒 Time: {time}

        🧾 Request Parameters:
        {json.dumps(request_params, indent=2)}

        📦 Resources:
        {json.dumps(resources, indent=2)}
        """

        if send_alert_IAM :
            # Publish to SNS - IAM Events
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"CloudTrail Alert: {event_name} in {account_id}",
                Message=message
            )
        if send_alert_others :
            # Publish to SNS - Other origins
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"CloudTrail Alert: {event_name} in {account_id}",
                Message=message
            )

        return {
            'statusCode': 200,
            'body': json.dumps('Alert sent successfully!')
        }
    
    except Exception as e:
        print("Error:", str(e))
        raise


