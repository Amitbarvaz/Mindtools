#!/bin/bash

# 1. Read environment variables from .env file
source .env

# 2. Print the value of ALLOWED_ADMIN_IPS
echo "Current allowed IPs: $ALLOWED_ADMIN_IPS"


# 3. Prompt the user for editing
read -p "Would you like to edit the IP list? (yes/no): " edit_ip_list

# 4. If the user wants to edit, prompt for new IP list
if [[ $edit_ip_list == "yes" ]]; then
  read -p "Enter the new comma-separated IP list: " new_ip_list

  if [[ $new_ip_list =~ ^[0-9.]+(,[0-9.]+)*$ ]]; then
    echo "Editing and Restarting Server..."

    # 5. Edit the .env file
    sed -i "s/ALLOWED_ADMIN_IPS=.*/ALLOWED_ADMIN_IPS=$new_ip_list/" .env

    source .env

    # 6. Restart the Docker Compose service
    docker compose -f DOCKER_COMPOSE_FILE_NAME! restart APP_SERVICE_NAME

    echo "Successfully updated allowed_admin_ips list and restarted the server."

  else
    echo "Invalid input. Exiting Script."
  fi
fi