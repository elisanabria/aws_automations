# 🛡️ AWS Ephemeral Resource Control Automation

This section provides an automated solution for managing **ephemeral EC2 and RDS resources** in an AWS Organization. It ensures resources tagged as `Ephemeral=True` are monitored for expiration and trigger alerts when their lifespan exceeds the defined threshold (default: **30 days**).

## 🔍 Overview

When a resource (EC2 or RDS) is created with the tag `Ephemeral=True`, this automation:

1. **Automatically adds metadata tags**:
   - `CreatedBy` – identifies the IAM user who created the resource.
   - `CreationDate` – timestamp of resource creation.

2. **Monitors resource age**:
   - Runs daily to evaluate if resources have exceeded the expiration period (default: 30 days).
   - If expired, it sends:
     - **Email notification** via SNS.
     - **Security Hub Finding** marking the control as failed.

## 🗺️ Architecture

This diagram shows the flow of automation across member and security accounts, highlighting resource tagging, monitoring, and alerting mechanisms.

![Architecture](ephemeral_resources_lifecycle/Architecture.png)

## 📦 Components

### 1. CloudFormation Templates

#### 🔐 Security Account Template
Deploys:
- **Tagger Lambda** – applies tags to new ephemeral resources.
- **Monitor Lambda** – evaluates expiration and sends alerts.
- **IAM roles and permissions** for both Lambdas.
- **EventBridge rule** to run the Monitor Lambda daily.

#### 🧩 Member Account Template (via StackSets)
Deploys:
- **EventBridge rule** that triggers the Tagger Lambda (in Security account) when a new EC2/RDS resource is created with `Ephemeral=True`.

### 2. Lambda Functions

#### ✍️ Tagger Lambda
Triggered by member accounts. Adds:
- `CreatedBy`
- `CreationDate`  
...to any resource tagged with `Ephemeral=True`.

#### ⏰ Monitor Lambda
Runs daily. Checks all resources with `Ephemeral=True` and:
- Sends an SNS email notification if expired.
- Adds a **Security Hub finding** for expired resources.

### 3. Test Scripts (`.sh` files)
Shell scripts to:
- Create sample EC2 or RDS instances.
- Apply necessary tags.
- Trigger the full automation flow for testing purposes.

## 🚀 Deployment

### Step 1: Deploy in Security Account
Use the `template-Security.yaml` to deploy:
- Tagger and Monitor Lambdas
- IAM roles
- SNS topic
- EventBridge scheduler

### Step 2: Deploy in Security Account
Use the `template-Members.yaml` to deploy:
- EventBridge Rules to trigger Tagger Lambda
- IAM roles
- CrossAccount permissions for Tagger

### Step 3: Test the Setup
Use the provided shell scripts to test the flow (CLI Scripts):
- `ec2_creation.sh` - Creates a test EC2 instance
- `rds_creation.sh` - Creates a test RDS instance

To test the expiration, you can change the CreationDate Tag of the resource and run the Monitor Lambda

## ⚙️ Configuration
You can customize the expiration period (default: 30 days) by updating the environment variable in the Monitor Lambda.

## 📧 Notifications & Security Findings
Notifications are sent via SNS (email).

Findings are published to AWS Security Hub as failed controls for expired resources.
