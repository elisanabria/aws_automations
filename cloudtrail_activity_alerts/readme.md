# 🛡️ AWS CloudTrail Alerts

This section provides an automated flow to monitor **CloudTrail (API Calls) Activity** in an AWS Organization. It ensures near real-time response to API Calls being monitored.

## 🔍 Overview

If, in one of the account being monitored, any of the specified API Call is triggered, this automation triggers a Lambda function that receives the Event Details, and sends them via SNS.

## 📦 Components

### 1. CloudFormation Templates

#### 🔐 Security Account Template
Deploys:
- **Alert Handler Lambda** – Triggered by EventBridge, used to process and send the Alert.
- **IAM role and permissions** for the Lambda function.
- **Resource permissions** Cross-Account for the EventBridge Rules deployed in the Member accounts.
- **SNS Topic** for Notifications.

#### 🧩 Member Account Template (via StackSets)
Deploys:
- **EventBridge rule** that triggers the Alert Handler Lambda (in Security account) when a CloudTrail Event matches the Event Pattern specified.

### 2. Lambda Function

#### 🚨 Alert Handler Lambda
- Triggered by EventBridge Rules.
- Receives and processes the CloudTrail Event, and sends an SNS email notification containing all the information.

## 🚀 Deployment

### Step 1: Upload Deployment files to S3
Download the files so you can reference them in your own Infrastructure. 
- If you use a centralized bucket, remember to update your resource policy!

### Step 2: Deploy in Security Account
Use the `security_account.yaml` as a Stack to deploy:
- Alert Handler Lambda
- IAM roles
- SNS topic

### Step 3: Deploy in Member Accounts
Use the `member_accounts.yaml` as a StackSet to deploy in your target accounts:
- EventBridge Rules to trigger Alert Handler Lambda
- IAM roles

### Step 3: Test the Setup
CloudTrail Events were not included, but you can test the pipeline generating any CloudTrail Event specified in the Event Pattern of the EB Rules!

## ⚙️ Configuration
You can customize the Event Pattern so they match exactly the activity to be monitored. Try to update the Template in your StackSet so you keep consistency... and not lose your mental health.

## 📧 Notifications & Security Findings
Notifications are sent via SNS (email).
