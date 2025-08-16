import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables (set in Lambda console)
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']  # DynamoDB table name
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']    # SNS topic ARN

def lambda_handler(event, context):
    """
    Lambda function that logs Docker image details into DynamoDB
    and sends an SNS notification after a successful ECR push.
    """

# Extract details from the event (supports both EventBridge and Jenkins formats)
    if "detail" in event:  # EventBridge ECR event
        image_tag = event['detail'].get('image-tag', 'unknown-tag')
        repository = event['detail'].get('repository-name', 'unknown-repo')
        pushed_by = event.get('account', 'unknown-user')
    else:  # Jenkins webhook (custom JSON)
        image_tag = event.get('image_tag', 'unknown-tag')
        repository = event.get('repository', 'unknown-repo')
        pushed_by = event.get('pushed_by', 'unknown-user')
    
    # Current timestamp
    timestamp = datetime.utcnow().isoformat()

    # Store details in DynamoDB
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.put_item(
        Item={
            'Repository': repository,
            'ImageTag': image_tag,
            'PushedBy': pushed_by,
            'Timestamp': timestamp
        }
    )

    # Create a notification message
    message = (
        f"Docker image pushed successfully!\n"
        f"Repository: {repository}\n"
        f"Tag: {image_tag}\n"
        f"Pushed By: {pushed_by}\n"
        f"Timestamp: {timestamp}"
    )

    # Publish the message to SNS
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message,
        Subject="ECR Image Push Notification"
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Lambda executed successfully!')
    }
