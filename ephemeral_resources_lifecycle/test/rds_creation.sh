#!/bin/bash

# Basic script for RDS DB Instance creation (Free Tier)

REGION="us-east-1"
DB_INSTANCE_ID="test-ephemeral-db"
DB_SUBNET_GROUP_NAME="default-rds-subnet-group"
DB_USERNAME="admin"
DB_PASSWORD="Ephemeral123!"  # Adjust this per your policy
DB_INSTANCE_CLASS="db.t3.micro"
DB_ENGINE="mysql"
DB_ALLOCATED_STORAGE=20
TAGS='Key=Ephemeral,Value=True Key=Name,Value=Test-Ephemeral'

# 1. Get default VPC
echo "Getting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --region $REGION \
  --query "Vpcs[0].VpcId" \
  --output text)

# 2. Get subnets in the default VPC
echo "Getting subnets for VPC $VPC_ID..."
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters Name=vpc-id,Values=$VPC_ID \
  --region $REGION \
  --query "Subnets[*].SubnetId" \
  --output text)

# 3. Create DB Subnet Group if it doesn't exist
echo "Creating subnet group if needed..."
aws rds describe-db-subnet-groups \
  --region $REGION \
  --db-subnet-group-name $DB_SUBNET_GROUP_NAME >/dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Creating DB subnet group $DB_SUBNET_GROUP_NAME..."
  aws rds create-db-subnet-group \
    --region $REGION \
    --db-subnet-group-name $DB_SUBNET_GROUP_NAME \
    --db-subnet-group-description "Default RDS subnet group" \
    --subnet-ids $SUBNET_IDS
else
  echo "DB subnet group already exists."
fi

# 4. Get existing default security group
SG_ID=$(aws ec2 describe-security-groups \
  --filters Name=vpc-id,Values=$VPC_ID Name=group-name,Values=default \
  --region $REGION \
  --query "SecurityGroups[0].GroupId" \
  --output text)

# 5. Launch RDS instance
echo "Creating RDS instance $DB_INSTANCE_ID..."
aws rds create-db-instance \
  --region $REGION \
  --db-instance-identifier $DB_INSTANCE_ID \
  --db-instance-class $DB_INSTANCE_CLASS \
  --engine $DB_ENGINE \
  --allocated-storage $DB_ALLOCATED_STORAGE \
  --master-username $DB_USERNAME \
  --master-user-password $DB_PASSWORD \
  --vpc-security-group-ids $SG_ID \
  --db-subnet-group-name $DB_SUBNET_GROUP_NAME \
  --no-publicly-accessible \
  --tags $TAGS \
  --backup-retention-period 0 \
  --no-multi-az \
  --storage-type gp2 \

echo "RDS creation initiated."
