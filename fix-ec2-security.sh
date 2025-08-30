#!/bin/bash
# Fix EC2 security group to allow traffic on port 8000

echo "===== EC2 Security Group Fix ====="
echo "$(date)"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "AWS CLI not found. Installing..."
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  sudo apt-get update && sudo apt-get install -y unzip
  unzip awscliv2.zip
  sudo ./aws/install
  rm -rf aws awscliv2.zip
fi

# Get instance metadata
echo "Getting instance metadata..."
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)

echo "Instance ID: $INSTANCE_ID"
echo "Region: $REGION"
echo "Public IP: $PUBLIC_IP"
echo "Public DNS: $PUBLIC_DNS"

# Configure AWS CLI if needed
echo "Would you like to configure AWS CLI? (y/n)"
read -p "> " configure_aws

if [ "$configure_aws" = "y" ]; then
  echo "Please enter your AWS credentials:"
  aws configure
fi

# Get security groups attached to the instance
echo "Getting security groups..."
SECURITY_GROUPS=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[*].Instances[*].SecurityGroups[*].{ID:GroupId,Name:GroupName}" \
  --output json \
  --region $REGION)

echo "Security Groups:"
echo $SECURITY_GROUPS | jq '.'

# Choose security group to modify
echo "Enter the security group ID to modify (e.g., sg-01234567):"
read -p "> " SECURITY_GROUP_ID

# Check if port 8000 is already open
PORT_OPEN=$(aws ec2 describe-security-groups \
  --group-ids $SECURITY_GROUP_ID \
  --query "SecurityGroups[*].IpPermissions[?ToPort==\`8000\`]" \
  --output json \
  --region $REGION)

if [[ $PORT_OPEN != "[]" ]]; then
  echo "Port 8000 is already open in this security group."
else
  # Add rule to allow traffic on port 8000
  echo "Adding rule to allow traffic on port 8000..."
  
  echo "Choose source IP for the security rule:"
  echo "1) Allow from anywhere (0.0.0.0/0)"
  echo "2) Allow from your current IP only"
  read -p "> " ip_choice
  
  if [ "$ip_choice" = "2" ]; then
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    SOURCE_IP="$MY_IP/32"
    echo "Using your current IP: $SOURCE_IP"
  else
    SOURCE_IP="0.0.0.0/0"
    echo "Using any IP: $SOURCE_IP"
  fi
  
  aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 8000 \
    --cidr $SOURCE_IP \
    --region $REGION
    
  # Also open port 80 if not already open
  PORT_80_OPEN=$(aws ec2 describe-security-groups \
    --group-ids $SECURITY_GROUP_ID \
    --query "SecurityGroups[*].IpPermissions[?ToPort==\`80\`]" \
    --output json \
    --region $REGION)
    
  if [[ $PORT_80_OPEN == "[]" ]]; then
    echo "Also adding rule for port 80 (frontend)..."
    aws ec2 authorize-security-group-ingress \
      --group-id $SECURITY_GROUP_ID \
      --protocol tcp \
      --port 80 \
      --cidr $SOURCE_IP \
      --region $REGION
  fi
fi

# Manual instructions if AWS CLI approach fails
echo ""
echo "===== Manual Instructions ====="
echo "If the above automation doesn't work, follow these steps in the AWS Console:"
echo "1. Go to EC2 > Security Groups"
echo "2. Find and select the security group for your instance"
echo "3. Click 'Edit inbound rules'"
echo "4. Add a rule: Custom TCP, Port 8000, Source 0.0.0.0/0"
echo "5. Add another rule: HTTP, Port 80, Source 0.0.0.0/0"
echo "6. Click 'Save rules'"
echo ""

echo "===== Checking Application Status ====="
# Check if the containers are running
docker ps

# Check the status of the backend
curl -s http://localhost:8000 || echo "Backend is not accessible locally"

echo ""
echo "===== Security Group Fix Complete ====="
echo "Try accessing your application again at:"
echo "Frontend: http://$PUBLIC_DNS"
echo "Backend API: http://$PUBLIC_DNS:8000"
echo "API Documentation: http://$PUBLIC_DNS:8000/api/docs or http://$PUBLIC_DNS:8000/docs"
