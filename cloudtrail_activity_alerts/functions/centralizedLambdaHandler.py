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

def handler(event, context):
    
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

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
        # Publish to SNS
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


