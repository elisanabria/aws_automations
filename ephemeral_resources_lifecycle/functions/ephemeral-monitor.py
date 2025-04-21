import boto3
import datetime
import json
import uuid
import os

accounts = os.getenv('ACCOUNT_IDS').split(',')
sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
expiration_days = os.getenv('EXPIRATION_DAYS')

def handler(event, context):

    today = datetime.datetime.utcnow().date()
    threshold = today - datetime.timedelta(days=expiration_days)
    finding = ""

    for account in accounts:
        role_arn = f"arn:aws:iam::{account}:role/EphemeralCrossAccountRole"
        creds = boto3.client("sts").assume_role(
            RoleArn=role_arn,
            RoleSessionName="MonitorEphemeral"
        )["Credentials"]

        ec2 = boto3.client("ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"])

        rds = boto3.client("rds",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

        sh = boto3.client("securityhub",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

        account_id = boto3.client('sts',
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        ).get_caller_identity()["Account"]

        region = boto3.Session().region_name

        instances = ec2.describe_instances(Filters=[
            {"Name": "tag:Ephemeral", "Values": ["True"]}
        ])

        for r in instances["Reservations"]:
            for inst in r["Instances"]:
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                creation_date_str = tags.get("CreationDate", "1970-01-01")
                creation_date = datetime.datetime.fromisoformat(creation_date_str).date()
                if creation_date <= threshold:
                    notify(inst["InstanceId"], tags, "AwsEc2Instance", region, account_id, sh)

        databases = rds.describe_db_instances()["DBInstances"]

        for inst in databases:
            arn = inst["DBInstanceArn"]
            tags_resp = rds.list_tags_for_resource(ResourceName=arn)
            tags = {t["Key"]: t["Value"] for t in tags_resp.get("TagList", [])}
            
            if tags.get("Ephemeral") == "True":
                try:
                    creation_date = datetime.datetime.strptime(tags["CreationDate"], "%Y-%m-%d").date()
                    if creation_date <= threshold:
                        notify(arn, tags, "AwsRdsDbInstance", region, account_id, sh)
                except Exception as e:
                    print(f"Failed to parse CreationDate for RDS {arn}: {e}")

def notify(resource_arn, tags, resource_type, region, account_id, sh):
    sns = boto3.client("sns")
    name = tags.get("Name", "N/A")
    creation_date = tags.get("CreationDate", "Unknown")
    
    tag_lines = "\n".join([f"{k}: {v}" for k, v in tags.items()])
    message = (
        f"Ephemeral {resource_type} expired\n\n"
        f"Resource ID: {resource_arn}\n"
        f"Name: {name}\n"
        f"CreationDate: {creation_date}\n\n"
        f"Tags:\n{tag_lines}"
    )
    
    sns.publish(
        TopicArn=sns_topic_arn,
        Subject=f"Ephemeral {resource_type} expired",
        Message=message
    )

    finding = {
        "SchemaVersion": "2018-10-08",
        "Id": str(uuid.uuid4()),
        "ProductArn": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default",
        "GeneratorId": "ephemeral-monitor",
        "AwsAccountId": account_id,
        "CreatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "UpdatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "Title": f"Ephemeral {resource_type} Expired",
        "Description": f"{resource_type} {resource_arn} exceeded {expiration_days}-day lifespan.",
        "Severity": {"Label": "MEDIUM"},
        "Resources": [{
            "Type": f"Aws{resource_type}",
            "Id": resource_arn,
            "Region": region,
            "Partition": "aws"
        }],
        "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
        "RecordState": "ACTIVE",
        "Compliance": {"Status": "FAILED"}
    }
    
    sh.batch_import_findings(Findings=[finding])
