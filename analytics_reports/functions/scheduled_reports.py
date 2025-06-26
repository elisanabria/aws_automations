import boto3
import time
import logging
import traceback
import json
import csv
import io
from io import StringIO
from botocore.client import Config

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
athena_client = boto3.client('athena')
sns_client = boto3.client('sns')
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
logs_client = boto3.client('logs')
identitystore_client = boto3.client('identitystore')

ATHENA_OUTPUT_BUCKET = 'athena-scheduled-reports'
ATHENA_OUTPUT_PREFIX = 'athena-results/'
CLOUDWATCH_OUTPUT_PREFIX = 'cloudwatch-results/'
IDENTITY_STORE_OUTPUT_PREFIX = 'identitystore-results/'

SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
CLOUDWATCH_LOG_GROUP = os.getenv('CLOUDWATCH_LOG_GROUP')
IDENTITY_STORE = os.getenv('IDENTITY_STORE')
MGMT_ACCT = os.getenv('MGMT_ACCT')
CLOUDWATCH_ACCOUNT = os.getenv('CLOUDWATCH_ACCOUNT') #This can be changed to an array if multiple CloudWatch logs need to be queried
ATHENA_DB_NAME = os.getenv('ATHENA_DB_NAME')


def assume_role(account_id, role_name, service_name):
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName=f"CrossAccountSession-{service_name}"
    )

    credentials = assumed_role['Credentials']

    # Return the requested client using the assumed role credentials
    return boto3.client(
        service_name,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

def execute_cloudwatch_query(query_string, logs_client):
    """Starts a CloudWatch Logs Insights query and returns its query ID."""
    try:
        response = logs_client.start_query(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            queryString=query_string,
            startTime=int((time.time() - 7 * 86400) * 1000),  # 7 days ago
            endTime=int(time.time() * 1000)  # Now
        )
        query_id = response.get("queryId")  # Ensure we return the queryId
        logger.info(f"Started CloudWatch query: {query_id}")
        return query_id
    except Exception as e:
        logger.error(f"Error executing CloudWatch query: {str(e)}", exc_info=True)
        return None

def execute_userID_commands(identitystore):
    """Mapping Email-UserIDs."""
    users = []
    next_token = None

    while True:
        params = {'IdentityStoreId': IDENTITY_STORE}
        if next_token:
            params['NextToken'] = next_token
        
        response = identitystore.list_users(**params)

        for user in response['Users']:
            email = next(
                (e['Value'] for e in user.get('Emails', []) if e.get('Primary')), 
                None
            )
            users.append({
                'UserId': user['UserId'],
                'Email': email or ''
            })

        next_token = response.get('NextToken')
        if not next_token:
            break
    
    return users
    
def save_dicts_to_s3_csv(dict_list, filename):
    #Save a list of dicts as a CSV file in S3 and return a presigned URL
    if not dict_list:
        logging.info("No results to save.")
        return "No results available"
    logging.info(f"Saving {len(dict_list)} rows to CSV: {filename}")

    field_names = list(dict_list[0].keys())

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=field_names)
    writer.writeheader()
    writer.writerows(dict_list)

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    s3_key = f"{CLOUDWATCH_OUTPUT_PREFIX}{timestamp}_{filename}"

    s3_client.put_object(
        Bucket=ATHENA_OUTPUT_BUCKET,
        Key=s3_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )

    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': ATHENA_OUTPUT_BUCKET, 'Key': s3_key},
        ExpiresIn=604800  # 7 days
    )

def wait_for_cloudwatch_query(query_id, logs_client, timeout=60):
    """Waits for the CloudWatch query to complete and returns results."""
    start_time = time.time()

    while True:
        response = logs_client.get_query_results(queryId=query_id)
        status = response.get("status")

        if status == "Complete":
            return response.get("results") if response.get("results") else []

        if status in ["Failed", "Cancelled"]:
            logger.error(f"Query {query_id} failed with status: {status}")
            return []

        if time.time() - start_time > timeout:
            logger.error(f"Query {query_id} timed out after {timeout} seconds.")
            return []

        time.sleep(2)  # Wait before checking again

def save_results_to_s3_csv(results, filename):
    """Saves CloudWatch query results as a CSV in S3 and returns a presigned URL."""
    try:
        if not results:
            logging.info("No results to save.")
            return "No results available"

        # Extract column names from results
        field_names = [field['field'] for field in results[0]] if results else []
        
        # Create an in-memory CSV buffer
        csv_buffer = io.StringIO()
        csv_writer = csv.DictWriter(csv_buffer, fieldnames=field_names)
        csv_writer.writeheader()

        # Write data rows
        for row in results:
            csv_writer.writerow({field['field']: field['value'] for field in row})

        # Define S3 path
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        s3_key = f"{CLOUDWATCH_OUTPUT_PREFIX}{timestamp}_{filename}"

        # Upload CSV to S3
        s3_client.put_object(
            Bucket=ATHENA_OUTPUT_BUCKET,
            Key=s3_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )

        logging.info(f"CSV file saved to s3://{ATHENA_OUTPUT_BUCKET}/{s3_key}")

        # Generate a presigned URL (valid for 24 hours)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': ATHENA_OUTPUT_BUCKET, 'Key': s3_key},
            ExpiresIn=604800  # 24 hours
        )

        return presigned_url

    except Exception as e:
        logging.error(f"Error saving CSV to S3: {str(e)}", exc_info=True)
        return "Error generating file"

def execute_query(query, database):
    """Starts an Athena query and handles errors."""
    try:
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={
                'OutputLocation': f's3://{ATHENA_OUTPUT_BUCKET}/{ATHENA_OUTPUT_PREFIX}'
            }
        )
        logger.info(f"Started query execution: {response['QueryExecutionId']}")
        return response['QueryExecutionId']
    except Exception as e:
        logger.error(f"Failed to start query execution: {str(e)}")
        logger.error("Traceback: " + traceback.format_exc())
        raise

def wait_for_query(query_execution_id, timeout=180):
    """Waits for the Athena query to complete, with a timeout."""
    start_time = time.time()

    while True:
        response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        status = response['QueryExecution']['Status']['State']

        if status == 'SUCCEEDED':
            return status
        elif status in ['FAILED', 'CANCELLED']:
            reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown reason')
            logger.error(f"Query {query_execution_id} failed with status: {status}. Reason: {reason}")
            return status

        if time.time() - start_time > timeout:
            raise TimeoutError(f"Query {query_execution_id} timed out after {timeout} seconds.")

        time.sleep(2)  # Wait before checking again

def generate_presigned_url(s3_path, expiration=604800):
    """Generates a presigned URL for the given S3 file."""
    try:
        if s3_path.startswith('s3://'):
            bucket_name, file_path = s3_path[5:].split('/', 1)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': file_path},
                ExpiresIn=expiration
            )
            return presigned_url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        logger.error("Traceback: " + traceback.format_exc())

    return None

def generate_report(queries_status):
    """Generate a detailed report including query, status, and presigned URL."""
    report = "Reporte semanal: Queries de Athena/CloudWatch + Control de Usuarios\n"
    for query_status in queries_status:
        query = query_status['query']
        title = query_status['title']
        status = query_status['status']
        result_url = query_status.get('result_url', 'No results available')

        report += f"\nTitle: {title}\n"
        report += f"\nQuery: \n{query}\n"
        report += f"\nExecution Status: {status}\n"
        report += f"\nReport URL: {result_url}\n"  # Provide downloadable URL
        report += f"\n"
        report += "-" * 50  # Separator for clarity
        report += f"\n"
    return report

def send_sns_report(report):
    """Sends the report via SNS."""
    try:
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=report,
            Subject='AWS: Scheduled Report'
        )
        logger.info(f"Report sent via SNS. MessageId: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send SNS message: {str(e)}")
        logger.error("Traceback: " + traceback.format_exc())

def lambda_handler(event, context):
    queries_status = []

    # Array of CloudWatch queries. They need Title and Query, the Log Group is passed in the function
    cloudwatch_queries = [
        {"title": "CW_Query Title", "query": "CW_Query"}
    ]

    # Array of Athena query IDs to be executed. The function assumes they are in the same account as itself
    athena_query_ids = [
        "Query_ID_1",
        "Query_ID_2",
        "Query_ID_3"
    ]
    database = ATHENA_DB_NAME
    
    named_query = ""
    query_title = ""
    query_string = ""

    user_ids = ""

   # Execute Athena Queries
    for query_id in athena_query_ids:
        try:
            named_query = athena_client.get_named_query(NamedQueryId=query_id)
            query_string = named_query['NamedQuery']['QueryString']
            query_title = named_query['NamedQuery']['Name']
            
            query_execution_id = execute_query(query_string, database)
            status = wait_for_query(query_execution_id)
            result_url = None

            if status == 'SUCCEEDED':
                result_location = athena_client.get_query_execution(QueryExecutionId=query_execution_id)['QueryExecution']['ResultConfiguration']['OutputLocation']
                logger.info(f"Athena Query results available at: {result_location}")
                result_url = generate_presigned_url(result_location)
            else:
                logger.error(f"Athena Query failed with status: {status}")

            queries_status.append({
                'title': query_title,
                'query': query_string,
                'status': status,
                'result_url': result_url
            })
        except Exception as e:
            logger.error(f"Error executing Athena query: {str(e)}")
            continue
          
 
    # Assume Role in CloudWatch Logs Account
    logs_client = assume_role(CLOUDWATCH_ACCOUNT, 'Cloudwatch_Reports', 'logs')

    # Execute CloudWatch Queries
    for query_data in cloudwatch_queries:
        try:
            query_title = query_data['title']
            query_string = query_data['query']
            logger.info(f"Executing CloudWatch query: {query_title}")

            query_id = execute_cloudwatch_query(query_string, logs_client)
            if query_id:
                results = wait_for_cloudwatch_query(query_id, logs_client)
                logger.info(f"Query Results for {query_title}: {results}")

                presigned_url = None
                if results:
                    presigned_url = save_results_to_s3_csv(results, f"{query_title.replace(' ', '_')}.csv")
                else:
                    presigned_url = "No results available"

                queries_status.append({
                    'title': query_title,
                    'query': query_string,
                    'status': 'SUCCEEDED' if results else 'NO RESULTS',
                    'result_url': presigned_url
                })
                logger.info(f"Query status updated: {queries_status[-1]}")
            else:
                logger.error(f"Query execution failed: {query_title}")
        except Exception as e:
            logger.error(f"Error executing CloudWatch query {query_title}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Final queries_status: {queries_status}")

    # Assume Role in Management Account
    identity_client = assume_role(MGMT_ACCT, 'Lambda_Reports', 'identitystore')
    user_ids = execute_userID_commands(identity_client)
    if user_ids:
        presigned_url = save_dicts_to_s3_csv(user_ids, filename='identity-center-users.csv')
        queries_status.append({
                    'title': 'Mail - User Correlation',
                    'query': 'list_users command in Mgmt Account',
                    'status': 'SUCCEEDED' if results else 'NO RESULTS',
                    'result_url': presigned_url
                })
    else:
        presigned_url = "No results available"    


    # Generate report and send via SNS
    if queries_status:
        report = generate_report(queries_status)
        send_sns_report(report)

    return {'queries_status': queries_status}
