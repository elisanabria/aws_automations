# 🛡️ AWS Analytics Report

This section provides an automated flow to run Organization Analytics, based on Athena query results from CloudTrail logs, CloudWatch query results, and User inventory from IAM Identity Center.

## 🔍 Overview

With a fixed schedule, the solution executes the queries in the corresponding services (Athena, CloudWatch), plus extracts the User inventory (email, UserID) from IAM Identity Center for further analysis.

## 📦 Components

### 1. CloudFormation Templates

#### 📄 Log Archive Account Template
Deploys:
- **Report Lambda** – Triggered by EventBridge Schedule, executes the queries.
- **IAM role and permissions** for the Lambda function.
- **EventBridge Schedule** to trigger the Lambda function.
- **SNS Topic** for Notifications.

#### 🧩 Cloudwatch Log Group - Cross-Account permissions
Deploys:
- **IAM Role, Permissions and Trust policy** that allows the Lambda in Log Archive account the execution of Cloudwatch Log Insights queries.

#### 🧩 IAM Identity Center - Cross-Account permissions
Deploys:
- **IAM Role, Permissions and Trust policy** that allows the Lambda in Management account to get the Users Inventory.

### 2. Lambda Function

#### 📚 Report Lambda
- Triggered by EventBridge Schedule - Fixed execution.
- Executes and processes Athena/Cloudwatch queries and Identity Center Users inventory, compiles the results in csv files and sends an SNS email notification containing all the information.

## 🚀 Deployment

### Step 1: Upload Deployment files to S3
Download the files so you can reference them in your own Infrastructure. 
- If you use a centralized bucket, remember to update your resource policy!

### Step 2: Deploy in Log Archive Account
Use the `logArchive_account.yaml` as a Stack to deploy:
- Report Lambda
- IAM roles
- EventBridge Scheduler
- SNS topic

### Step 3: Deploy in Cloudwatch Logs Accounts
Use the `cloudwatch_account.yaml` as a Stack to deploy in the Account containing the Cloudwatch Logs:
- IAM role/policies to be assumed by Lambda

### Step 4: Deploy in Management Account
Use the `identitystore_account.yaml` as a StackSet to deploy in your target accounts:
- IAM role/policies to be assumed by Lambda

### Step 5: Test the Setup
You can wait for the schedule or manually trigger the Lambda function, it should send an email report with all your information!

## ⚙️ Configuration
At least for now, you need to manually change the Lambda Code, adding the query IDs of your Athena queries, and/or your Cloudwatch queries. But this is a voluntary WIP so this can change in the futire!

## 📧 Notifications & Security Findings
Notifications are sent via SNS (email).
