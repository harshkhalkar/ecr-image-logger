# ECR Image Event Logger

This project implements an **event-driven workflow** on AWS that tracks container images pushed to **Amazon Elastic Container Registry (ECR)** . It stores metadata in **Amazon DynamoDB** and send notifications through **Amazon SNS**.

The solution ensure visibility & auditing for container images in a centralized, automated way.

## Overview

Whenever a new image is pushed to **Amazon ECR**:

1. **Amazon EventBridge** captures the push event.
2. **AWS Lambda** is triggered.
3. Lambda extracts image metadata (e.g., repository name, tag, etc).
4. Metadata is stored in **Amazon DynamoDB** for tracking.
5. A notification is sent via **Amazon SNS** to alert subscribers.

## Architecture Diagram

![Architecture-Diagram](./doc/Architecture%20Diagram%20Overview.png)

**Flow:**
1. Jenkins pushes a Docker Image -> **Amazon ECR**
2. **EventBridge** captures image push event
3. **Lambda** executes logic
    - Stores metadata -> **DynamoDB**
    - Send notification -> **SNS**

## Reposiotry Structure

```bash
.
├── Jenkinsfile                     # CI/CD pipeline
├── LICENSE                         # License file for the project
├── README.md                       # Main documentation file
├── lambda_function.py              # Lambda function
└── doc/
    └── Architecture Diagram Overview.png  
```

## Setup Instructions

### 1. Create a DynamoDB Table

1. Go to **DynamoDB** → **Create Table**.
2. Table name:

    ```text
    ECRImageLogs
    ```

3. Partition key:

    ```text
    Repository (String)
    ```

4. Sort key:

    ```text
    ImageTag (String)
    ```

5. Leave all other options as default.
6. Click **Create Table**.

---

### 2. Set Up SNS Topic

1. Go to **AWS SNS** → **Create topic**.
2. Choose **Standard** as the topic type.
3. Name the topic:

    ```text
    ECRPushNotifications
    ```

4. Create a subscription:
    - **Protocol**: Email
    - **Endpoint**: *Your email address*
5. Confirm the subscription from your email inbox.

---

### 3. Create the Lambda Function

1. Go to **AWS Lambda** → **Create function**.
2. Choose the following settings:
    - **Author from scratch**
    - Function name:

        ```text
        ECRImageLogger
        ```

    - Runtime:

        ```text
        Python 3.12
        ```

3. Execution role:
    - Create a new IAM role named:

        ```text
        ECRImageLoggerIAMRole
        ```

    - Attach the following policies:
        - `AmazonDynamoDBFullAccess`
        - `AmazonSNSFullAccess`

4. Navigate to the **Code** tab and paste the following code:

    ```python
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
    ```

5. Add environment variables:

    | Key              | Value             |
    |------------------|-------------------|
    | `DYNAMODB_TABLE` | `ECRImageLogs`    |
    | `SNS_TOPIC_ARN`  | *Your SNS ARN*    |

6. Increase **Timeout** to:

    ```text
    1 minute
    ```
---

### 4. Create EventBridge Rule (Trigger Lambda After ECR Push)

1. Go to **Amazon EventBridge** → **Rules** → **Create Rule**.
2. Set the following:
   - **Name**:

     ```text
     ECRPushTrigger
     ```

   - **Event bus**:

     ```text
     default
     ```

3. Define the **Event pattern**:

    ```json
    {
        "source": ["aws.ecr"],
        "detail-type": ["ECR Image Action"],
        "detail": {
            "action-type": ["PUSH"],
            "result": ["SUCCESS"]
        }
    }
    ```

4. Alternatively, upload the pattern as a JSON file.
5. Add a **Target**:
   - Type: **Lambda function**
   - Function name:

     ```text
     ECRImageLogger
     ```

6. Save the rule.

---

### 5. Jenkins Pipeline

1. **Prerequisite**: [Jenkins Server Setup](https://github.com/harshkhalkar/jenkins.git)
2. Access the Jenkins server UI.
3. Create a new item:
   - Name:

     ```text
     Docker-Push-CI/CD
     ```

   - Type: **Pipeline**
4. Configure the environment based on your requirements.
5. Paste the following Pipeline Script:

    ```groovy
    pipeline {
        agent any

        stages {
            stage('Install Docker') {
                steps {
                    echo 'Installing Docker (if not already installed)...'
                    sh '''
                        if ! command -v docker &> /dev/null; then
                            sudo apt update -y
                            sudo apt install -y docker.io
                            sudo systemctl start docker
                        fi
                    '''
                }
            }

            stage('Install AWS CLI') {
                steps {
                    echo 'Installing AWS CLI (if not already installed)...'
                    sh '''
                        if ! command -v aws &> /dev/null; then
                            sudo apt update -y
                            sudo apt install -y unzip
                            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                            unzip -o awscliv2.zip
                            sudo ./aws/install
                        fi
                    '''
                }
            }

            stage('Git Checkout') {
                steps {
                    sh '''
                        sudo mkdir -p /docker
                        cd /docker
                    '''
                    checkout([$class: 'GitSCM',
                        branches: [[name: '*/main']],
                        userRemoteConfigs: [[url: 'https://github.com/harshkhalkar/student-registration-flask-application.git']]
                    ])
                    sh 'rm -rf LICENSE README.md kubernetes docker-compose.yml init.sql Jenkinsfile'
                    sh 'ls -l'
                }
            }

            stage('Build and Run Docker Container') {
                steps {
                    sh '''
                        sudo docker build -t demo/purpose:v2 .
                        sudo docker run -d -p 5000:5000 --name pyapp demo/purpose:v2
                    '''
                }
            }

            stage('Run Tests') {
                steps {
                    echo 'Running tests inside container...'
                    sh '''
                        sudo docker ps
                        curl -s localhost:5000 || echo "Flask app not reachable"
                        sudo docker exec pyapp ls -l
                        sudo docker exec pyapp ls -l tests
                        sudo docker exec pyapp python3 -m unittest discover -s tests -t .
                    '''
                }
            }

            stage('Push to ECR') {
                steps {
                    sh '''
                        aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 873579225118.dkr.ecr.us-east-1.amazonaws.com
                        sudo docker tag demo/purpose:v2 873579225118.dkr.ecr.us-east-1.amazonaws.com/demo/purpose:v2
                        sudo docker push 873579225118.dkr.ecr.us-east-1.amazonaws.com/demo/purpose:v2
                    '''
                }
            }
        }

        post {
            always {
                echo 'Cleaning up Docker resources...'
                sh '''
                    sudo docker stop pyapp || true
                    sudo docker rm pyapp || true
                    sudo docker rmi demo/purpose:v2 || true
                    sudo docker rmi $(sudo docker images -q) || true
                '''
            }
        }
    }
    ```

6. Click **Save** and **Run** the pipeline.

---

## Test the Setup

1. **Run the Jenkins Pipeline**
   - Jenkins should:
     - Build the Docker image
     - Push it to Amazon ECR

2. **Verify EventBridge Trigger**
   - Go to **Amazon EventBridge** → **Rules**.
   - Confirm that your rule was triggered.

3. **Check DynamoDB**
   - Go to the `ECRImageLogs` table → **Items**
   - You should see a new record containing:
     - Repository name
     - Image tag
     - Pushed by
     - Timestamp

4. **Check SNS Notification**
   - You should receive an email notification with ECR image push details.

5. **Check Lambda Logs**
   - Go to **CloudWatch Logs** → **Log groups**
   - Find the log group for `ECRImageLogger`
   - Confirm the Lambda executed successfully and logged image metadata.

---
