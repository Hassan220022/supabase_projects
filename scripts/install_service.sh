#!/bin/bash

# Install the Supabase Project Generator as a systemd service

echo "Installing Supabase Project Generator service..."

# Copy the service file to systemd directory
cp /root/supabase_project_generator/supabase-generator.service /etc/systemd/system/

# Reload systemd to recognize the new service
systemctl daemon-reload

# Enable the service to start on boot
systemctl enable supabase-generator.service

# Start the service
systemctl start supabase-generator.service

# Check the status
echo "Service status:"
systemctl status supabase-generator.service --no-pager

echo "Supabase Project Generator service installed and started successfully!"
echo "Access the web interface at http://localhost:8000"
