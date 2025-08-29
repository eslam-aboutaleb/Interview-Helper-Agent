#!/bin/bash

# Script to update .env for EC2 deployment

EC2_PUBLIC_DNS="ec2-13-48-71-121.eu-north-1.compute.amazonaws.com"

sed -i "s|REACT_APP_API_URL=http://your-ec2-public-ip:8000|REACT_APP_API_URL=http://$EC2_PUBLIC_DNS:8000|g" .env

echo "Updated .env with EC2 public DNS: $EC2_PUBLIC_DNS"
echo "Environment configuration updated successfully!"
