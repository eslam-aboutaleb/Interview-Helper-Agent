#!/bin/bash
# This script sets up a fresh EC2 instance for the Interview Helper application
# Run with: bash ec2-setup.sh

echo "===== Starting EC2 Initial Setup ====="
echo "$(date)"

# Step 1: Update system packages
echo "===== Updating system packages ====="
sudo apt update
sudo apt upgrade -y

# Step 2: Install Docker
echo "===== Installing Docker ====="
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Step 3: Install Docker Compose
echo "===== Installing Docker Compose ====="
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Step 4: Add current user to docker group
echo "===== Configuring Docker permissions ====="
sudo usermod -aG docker $USER
echo "NOTE: You may need to log out and log back in for group changes to take effect"

# Step 5: Start Docker service
echo "===== Starting Docker service ====="
sudo systemctl start docker
sudo systemctl enable docker
sudo systemctl status docker

# Step 6: Setup swap space for better performance
echo "===== Setting up swap space (2GB) ====="
if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "Swap space added"
else
  echo "Swap file already exists"
fi

# Step 7: Install additional useful tools
echo "===== Installing additional tools ====="
sudo apt install -y git htop tmux

# Step 8: Update .env file with current EC2 DNS
echo "===== Updating environment variables ====="
EC2_PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

if [ -n "$EC2_PUBLIC_DNS" ]; then
  # Update the .env file if it exists
  if [ -f .env ]; then
    sed -i "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=http://$EC2_PUBLIC_DNS:8000|g" .env
    echo "Updated API URL to http://$EC2_PUBLIC_DNS:8000"
  else
    # Create a new .env file
    cat > .env << EOF
# Gemini API Key
GEMINI_API_KEY=#############################

# Database connection for Docker Compose setup
DATABASE_URL=postgresql://postgres:postgres@db:5432/interviews
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=interviews

# Frontend API URL with correct http:// prefix
REACT_APP_API_URL=http://$EC2_PUBLIC_DNS:8000
EOF
    echo "Created new .env file with EC2 public DNS"
  fi
elif [ -n "$EC2_PUBLIC_IP" ]; then
  # Fallback to IP if DNS isn't available
  if [ -f .env ]; then
    sed -i "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=http://$EC2_PUBLIC_IP:8000|g" .env
    echo "Updated API URL to http://$EC2_PUBLIC_IP:8000"
  else
    # Create a new .env file
    cat > .env << EOF
# Gemini API Key
GEMINI_API_KEY=AIzaSyAJYD-VgEMtCHQMyoGCes72z5UZyU75Z_U

# Database connection for Docker Compose setup
DATABASE_URL=postgresql://postgres:postgres@db:5432/interviews
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=interviews

# Frontend API URL with correct http:// prefix
REACT_APP_API_URL=http://$EC2_PUBLIC_IP:8000
EOF
    echo "Created new .env file with EC2 public IP"
  fi
else
  echo "Warning: Could not get EC2 public DNS or IP"
  echo "You will need to manually update REACT_APP_API_URL in your .env file"
fi

# Step 9: Make deployment scripts executable
echo "===== Setting script permissions ====="
chmod +x ec2-deploy.sh
if [ -f frontend-build.sh ]; then
  chmod +x frontend-build.sh
fi
if [ -f local-build-deploy.sh ]; then
  chmod +x local-build-deploy.sh
fi

echo "===== EC2 Setup Complete ====="
echo "Your EC2 instance is now ready for deployment!"
echo "Next steps:"
echo "1. If you logged in as a non-root user, you may need to log out and log back in"
echo "   for the docker group permissions to take effect"
echo "2. Run the deployment script: ./ec2-deploy.sh"
echo "3. For better performance on smaller instances, consider using:"
echo "   ./ec2-deploy.sh --prebuilt (after building locally)"
echo "$(date)"
