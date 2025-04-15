# AWS CLI Command
# Creates a basic EC2 instance for testing purposes
aws ec2 run-instances \
  --image-id $(aws ec2 describe-images \
      --owners amazon \
      --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" "Name=state,Values=available" \
      --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
      --output text) \
  --instance-type t2.micro \
  --count 1 \
  --network-interfaces "[
    {
      \"DeviceIndex\": 0,
      \"AssociatePublicIpAddress\": false,
      \"SubnetId\": \"$(aws ec2 describe-subnets \
        --filters Name=default-for-az,Values=true \
        --query 'Subnets[0].SubnetId' --output text)\",
      \"Groups\": [\"$(aws ec2 describe-security-groups \
        --filters Name=group-name,Values=default \
        --query 'SecurityGroups[0].GroupId' --output text)\"]
    }
  ]" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Test-Ephemeral},{Key=Ephemeral,Value=True}]' \
  --monitoring Enabled=false 
