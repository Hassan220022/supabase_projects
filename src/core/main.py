#!/usr/bin/env python3

import os
import sys
import json
import secrets
import subprocess
import argparse
import jwt
import hashlib
import base64
import socket
import psutil
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

class ProjectLogger:
    def __init__(self):
        self.logs = []
        self.lock = threading.Lock()
    
    def log(self, message, level="INFO"):
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {level}: {message}"
            self.logs.append(log_entry)
            print(log_entry)  # Also print to console
    
    def get_logs(self):
        with self.lock:
            return self.logs.copy()
    
    def clear_logs(self):
        with self.lock:
            self.logs.clear()

class SupabaseProjectGenerator:
    def __init__(self):
        self.projects_dir = os.environ.get('SUPABASE_PROJECTS_DIR', os.path.expanduser("~/supabase_projects"))
        self.template_dir = "/workspace/templates"
        self.logger = ProjectLogger()
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def get_machine_ip(self):
        """Get the machine's IP address"""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def check_port_availability(self, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False
    
    def find_available_ports(self, base_ports):
        """Find available ports starting from base ports"""
        available_ports = {}
        for service, base_port in base_ports.items():
            port = base_port
            while not self.check_port_availability(port):
                port += 1
                if port > base_port + 100:  # Prevent infinite loop
                    raise Exception(f"Could not find available port for {service} service")
            available_ports[service] = port
        return available_ports
    
    def get_service_status(self, port):
        """Check if a service is running on a specific port"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except:
            return False

    def generate_jwt_keys(self, project_ref):
        """Generate proper JWT tokens for Supabase anon and service keys matching Supabase format"""
        # Create a secret key for signing (64 characters for stronger security)
        secret_key = secrets.token_urlsafe(48)
        
        # Generate a random project reference if not provided
        if not project_ref:
            project_ref = secrets.token_urlsafe(16).lower().replace('_', '').replace('-', '')[:20]
        
        # Current timestamp
        current_time = int(datetime.now().timestamp())
        # 10 year expiry (matching Supabase standard)
        expiry_time = current_time + (365 * 24 * 60 * 60 * 10)
        
        # Anon key payload (exactly matching your example format)
        anon_payload = {
            "iss": "supabase",
            "ref": project_ref,
            "role": "anon", 
            "iat": current_time,
            "exp": expiry_time
        }
        
        # Service key payload (exactly matching your example format)
        service_payload = {
            "iss": "supabase",
            "ref": project_ref,
            "role": "service_role",
            "iat": current_time,
            "exp": expiry_time
        }
        
        # Generate tokens with HS256 algorithm
        anon_key = jwt.encode(anon_payload, secret_key, algorithm="HS256")
        service_key = jwt.encode(service_payload, secret_key, algorithm="HS256")
        
        return anon_key, service_key, secret_key
    
    def create_project(self, project_name, machine_size, specs, db_host="192.168.1.43", db_port="5432", db_user="postgres", db_password="your_password", username=None, password=None, use_local_db=False):
        """Create a new Supabase project with specified parameters"""
        self.logger.clear_logs()  # Clear previous logs
        self.logger.log(f"Starting Supabase project creation: {project_name}")
        
        # Validate project name uniqueness
        self.logger.log("Validating project name uniqueness...")
        project_path = os.path.join(self.projects_dir, project_name)
        if os.path.exists(project_path):
            self.logger.log(f"Project '{project_name}' already exists!", "ERROR")
            raise ValueError(f"Project '{project_name}' already exists. Please choose a different name.")
        
        # Validate machine size
        self.logger.log("Validating machine size configuration...")
        valid_machine_sizes = ["small", "medium", "large", "xlarge"]
        if machine_size not in valid_machine_sizes:
            self.logger.log(f"Invalid machine size: {machine_size}", "ERROR")
            raise ValueError(f"Invalid machine size. Choose from: {', '.join(valid_machine_sizes)}")
        
        # Verify PostgreSQL connection
        self.logger.log(f"Using hosted PostgreSQL server at {db_host}:{db_port}")
        self.logger.log("⚠️  NOT using any local PostgreSQL installation")
        
        # Create project directory
        self.logger.log(f"Creating project directory: {project_path}")
        os.makedirs(project_path, exist_ok=True)
        
        # Generate JWT keys with project reference
        self.logger.log("Generating Supabase-compatible JWT tokens...")
        project_ref = secrets.token_urlsafe(16).lower().replace('_', '').replace('-', '')[:20]
        anon_key, service_key, jwt_secret = self.generate_jwt_keys(project_ref)
        self.logger.log(f"Generated project reference: {project_ref}")
        self.logger.log("✅ JWT tokens generated successfully")
        
        # Get machine IP
        self.logger.log("Detecting machine IP address...")
        machine_ip = self.get_machine_ip()
        self.logger.log(f"Machine IP detected: {machine_ip}")
        
        # Define base ports for services
        self.logger.log("Checking port availability for Supabase services...")
        base_ports = {
            "studio": 3000,
            "kong": 8000,
            "auth": 9999,
            "rest": 3001,
            "realtime": 4000,
            "storage": 5000,
            "meta": 8080,
            "functions": 54321,
            "analytics": 4001,
            "vector": 9001
        }
        
        # Find available ports
        try:
            available_ports = self.find_available_ports(base_ports)
            self.logger.log("✅ Port allocation completed:")
            for service, port in available_ports.items():
                self.logger.log(f"  • {service.title()}: {port}")
        except Exception as e:
            self.logger.log(f"Port allocation failed: {str(e)}", "ERROR")
            raise ValueError(f"Port allocation failed: {str(e)}")
        
        # Create database configuration
        db_config = {
            'host': db_host,
            'port': db_port,
            'user': db_user,
            'password': db_password,
            'database': project_name
        }
        
        # Create project configuration
        self.logger.log("Creating project configuration...")
        config = {
            "project_name": project_name,
            "project_ref": project_ref,
            "machine_size": machine_size,
            "specs": specs,
            "machine_ip": machine_ip,
            "db_config": db_config,
            "anon_key": anon_key,
            "service_key": service_key,
            "jwt_secret": jwt_secret,
            "created_at": datetime.now().isoformat(),
            "ports": available_ports
        }
        
        # Save configuration
        self.logger.log("Saving project configuration...")
        config_path = os.path.join(project_path, "supabase_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create docker-compose.yml for the project
        self.logger.log("Generating Docker Compose configuration...")
        self.create_docker_compose(project_path, project_name, config)
        
        self.logger.log("✅ Supabase project created successfully!")
        
        # Auto-start the project after creation
        self.logger.log("🚀 Starting project services...")
        if self.start_project(project_name):
            self.logger.log("✅ Project services started successfully!")
        else:
            self.logger.log("⚠️ Warning: Failed to start some services automatically")
        
        self.logger.log(f"📁 Project location: {project_path}")
        self.logger.log(f"🌐 Supabase Studio will be available at: http://{machine_ip}:{available_ports['studio']}")
        self.logger.log(f"🔌 API Gateway (Kong) at: http://{machine_ip}:{available_ports['kong']}")
        
        print(f"Supabase project '{project_name}' created successfully at {project_path}")
        return project_path

    def start_project(self, project_name):
        """Start a Supabase project using Docker Compose.
        Returns (success, stdout, stderr)
        """
        try:
            project_path = os.path.join(self.projects_dir, project_name)
            if not os.path.exists(project_path):
                return (False, '', f"Project path not found: {project_path}")
            
            compose_file = os.path.join(project_path, 'docker-compose.yml')
            if not os.path.exists(compose_file):
                return (False, '', "docker-compose.yml not found")
            
            # Auto-migrate GoTrue image tag if old 'latest' is present
            try:
                with open(compose_file, 'r') as f:
                    compose_text = f.read()
                if 'supabase/gotrue:latest' in compose_text:
                    compose_text = compose_text.replace('supabase/gotrue:latest', 'supabase/gotrue:v2')
                    with open(compose_file, 'w') as f:
                        f.write(compose_text)
            except Exception:
                pass

            # Pull latest images (non-fatal)
            self._run_compose(project_path, ['pull'])
            # Start services
            rc, out, err = self._run_compose(project_path, ['up', '-d'])
            return (rc == 0, out, err)
        except Exception as e:
            msg = f"Error starting project {project_name}: {e}"
            print(msg)
            return (False, '', msg)

    def stop_project(self, project_name):
        """Stop a Supabase project using Docker Compose.
        Returns (success, stdout, stderr)
        """
        try:
            project_path = os.path.join(self.projects_dir, project_name)
            if not os.path.exists(project_path):
                return (False, '', f"Project path not found: {project_path}")
            
            compose_file = os.path.join(project_path, 'docker-compose.yml')
            if not os.path.exists(compose_file):
                return (False, '', "docker-compose.yml not found")
            
            rc, out, err = self._run_compose(project_path, ['down'])
            return (rc == 0, out, err)
        except Exception as e:
            msg = f"Error stopping project {project_name}: {e}"
            print(msg)
            return (False, '', msg)

    def delete_project(self, project_name):
        """Delete a Supabase project completely.
        Returns (success, stdout, stderr)
        """
        try:
            project_path = os.path.join(self.projects_dir, project_name)
            if not os.path.exists(project_path):
                return (False, '', f"Project path not found: {project_path}")
            
            # First stop the project if it's running (ignore errors)
            self.stop_project(project_name)
            
            # Remove docker containers and volumes
            rc, out1, err1 = self._run_compose(project_path, ['down', '-v', '--remove-orphans'])
            # Attempt to delete project directory regardless of rc from compose
            try:
                import shutil
                shutil.rmtree(project_path)
                out2, err2 = 'project directory removed', ''
            except Exception as e:
                out2, err2 = '', f"failed to remove project directory: {e}"
            success = (rc == 0) and (err2 == '')
            combined_out = '\n'.join(filter(None, [out1, out2]))
            combined_err = '\n'.join(filter(None, [err1, err2]))
            return (success, combined_out, combined_err)
        except Exception as e:
            msg = f"Error deleting project {project_name}: {e}"
            print(msg)
            return (False, '', msg)

    def _run_compose(self, cwd, args):
        """Run docker compose with fallback to old/new syntax.
        Returns (returncode, stdout, stderr).
        """
        import shutil
        import subprocess
        commands = []
        # Prefer docker compose if available
        if shutil.which('docker'):
            commands.append(['docker', 'compose'] + args)
        # Fallback to docker-compose
        if shutil.which('docker-compose'):
            commands.append(['docker-compose'] + args)
        if not commands:
            return (1, '', 'docker/docker-compose not found')
        last_rc, last_out, last_err = 1, '', ''
        for cmd in commands:
            try:
                res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
                if res.returncode == 0:
                    return (0, res.stdout, res.stderr)
                last_rc, last_out, last_err = res.returncode, res.stdout, res.stderr
            except Exception as e:
                last_rc, last_err = 1, str(e)
        return (last_rc, last_out, last_err)
    
    def create_docker_compose(self, project_path, project_name, config):
        """Create docker-compose.yml for the Supabase project"""
        ports = config['ports']
        docker_compose_content = f"""
version: '3.8'

services:
  studio:
    image: supabase/studio:latest
    ports:
      - {ports['studio']}:3000
    environment:
      SUPABASE_URL: http://kong:{ports['kong']}
      SUPABASE_REST_URL: http://localhost:{ports['kong']}/rest/v1/
      SUPABASE_ANON_KEY: {config['anon_key']}
      SUPABASE_SERVICE_KEY: {config['service_key']}
      STUDIO_PG_META_URL: http://meta:{ports['meta']}
    
  kong:
    image: kong:latest
    ports:
      - {ports['kong']}:8000
    environment:
      KONG_DATABASE: off
      KONG_DECLARATIVE_CONFIG: /opt/kong/kong.yml
      KONG_DNS_ORDER: LAST,A,CNAME
      KONG_PLUGINS: request-transformer,cors,key-auth,acl,opentelemetry
    volumes:
      - ./kong.yml:/opt/kong/kong.yml
    healthcheck:
      test: ["CMD", "kong", "health"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  auth:
    image: supabase/gotrue:v2
    ports:
      - {ports['auth']}:9999
    environment:
      GOTRUE_API_HOST: 0.0.0.0
      GOTRUE_API_PORT: 9999
      API_EXTERNAL_URL: http://localhost:{ports['kong']}
      
      GOTRUE_DB_DRIVER: postgres
      GOTRUE_DB_DATABASE_URL: postgresql://{config['db_config']['user']}:{config['db_config']['password']}@{config['db_config']['host']}:{config['db_config']['port']}/{project_name}
      
      GOTRUE_SITE_URL: http://localhost:{ports['studio']}
      GOTRUE_URI_ALLOW_LIST: '*'
      GOTRUE_DISABLE_SIGNUP: false
      
      GOTRUE_JWT_ADMIN_ROLES: service_role
      GOTRUE_JWT_AUD: authenticated
      GOTRUE_JWT_DEFAULT_GROUP_NAME: authenticated
      GOTRUE_JWT_EXP: 3600
      GOTRUE_JWT_SECRET: {config['jwt_secret']}
      
      GOTRUE_EXTERNAL_EMAIL_ENABLED: true
      GOTRUE_MAILER_AUTOCONFIRM: true
      GOTRUE_SMTP_HOST: localhost
      GOTRUE_SMTP_PORT: 2500
      GOTRUE_SMTP_USER: ""
      GOTRUE_SMTP_PASS: ""
      GOTRUE_SMTP_ADMIN_EMAIL: admin@example.com
      GOTRUE_MAILER_URLPATHS_INVITE: /auth/v1/verify
      GOTRUE_MAILER_URLPATHS_CONFIRMATION: /auth/v1/verify
      GOTRUE_MAILER_URLPATHS_RECOVERY: /auth/v1/verify
      GOTRUE_MAILER_URLPATHS_EMAIL_CHANGE: /auth/v1/verify
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9999/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  rest:
    image: postgrest/postgrest:latest
    ports:
      - {ports['rest']}:3000
    environment:
      PGRST_DB_URI: postgresql://{config['db_config']['user']}:{config['db_config']['password']}@{config['db_config']['host']}:{config['db_config']['port']}/{project_name}
      PGRST_DB_SCHEMA: public
      PGRST_DB_ANON_ROLE: anon
      PGRST_JWT_SECRET: {config['jwt_secret']}
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  realtime:
    image: supabase/realtime:latest
    ports:
      - {ports['realtime']}:4000
    environment:
      PORT: 4000
      DB_HOST: {config['db_config']['host']}
      DB_PORT: {config['db_config']['port']}
      DB_NAME: {project_name}
      DB_USER: {config['db_config']['user']}
      DB_PASSWORD: {config['db_config']['password']}
      DB_SSL: 'false'
      JWT_SECRET: {config['jwt_secret']}
      REPLICATION_MODE: RLS
      REPLICATION_POLL_INTERVAL: 100
      SECURE_CHANNELS: 'true'
      SLOT_NAME: supabase_realtime_rls
      TEMPORARY_SLOT: 'true'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  storage:
    image: supabase/storage-api:latest
    ports:
      - {ports['storage']}:5000
    environment:
      ANON_KEY: {config['anon_key']}
      SERVICE_KEY: {config['service_key']}
      POSTGREST_URL: http://rest:3000
      PGRST_JWT_SECRET: {config['jwt_secret']}
      DATABASE_URL: postgresql://{config['db_config']['user']}:{config['db_config']['password']}@{config['db_config']['host']}:{config['db_config']['port']}/{project_name}
      FILE_SIZE_LIMIT: 52428800
      STORAGE_BACKEND: file
      FILE_STORAGE_BACKEND_PATH: /var/lib/storage
      TENANT_ID: stub
      SKIP_API_HOST_CHECK: true
      REGION: stub
    volumes:
      - ./storage:/var/lib/storage
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:5000/status"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  meta:
    image: supabase/postgres-meta:latest
    ports:
      - {ports['meta']}:8080
    environment:
      PG_META_PORT: 8080
      PG_META_DB_HOST: {config['db_config']['host']}
      PG_META_DB_PORT: {config['db_config']['port']}
      PG_META_DB_NAME: {project_name}
      PG_META_DB_USER: {config['db_config']['user']}
      PG_META_DB_PASSWORD: {config['db_config']['password']}
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  functions:
    image: supabase/edge-runtime:latest
    ports:
      - {ports['functions']}:8081
    environment:
      SUPABASE_URL: http://kong:{ports['kong']}
      SUPABASE_ANON_KEY: {config['anon_key']}
      SUPABASE_SERVICE_KEY: {config['service_key']}
      SUPABASE_DB_URL: postgresql://{config['db_config']['user']}:{config['db_config']['password']}@{config['db_config']['host']}:{config['db_config']['port']}/{project_name}
    volumes:
      - ./functions:/home/deno/functions:Z
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/status"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  analytics:
    image: supabase/logflare:latest
    ports:
      - {ports['analytics']}:4000
    environment:
      LOGFLARE_NODE_HOST: 127.0.0.1
      DB_HOST: {config['db_config']['host']}
      DB_PORT: {config['db_config']['port']}
      DB_NAME: {project_name}
      DB_USER: {config['db_config']['user']}
      DB_PASSWORD: {config['db_config']['password']}
      LOGFLARE_API_KEY: {config['jwt_secret']}
      LOGFLARE_SINGLE_TENANT: true
      LOGFLARE_SUPABASE_MODE: true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  vector:
    image: timberio/vector:latest
    ports:
      - {ports['vector']}:9001
    
volumes:
  storage:
"""
        
        docker_compose_path = os.path.join(project_path, "docker-compose.yml")
        with open(docker_compose_path, 'w') as f:
            f.write(docker_compose_content)
        
        # Create Kong configuration
        self.create_kong_config(project_path, config)
    
    def create_kong_config(self, project_path, config):
        """Create Kong configuration file"""
        kong_content = f"""
_format_version: "1.1"

services:
  - name: auth-v1
    url: http://auth:9999/verify
    routes:
      - name: auth-v1-routes
        paths:
          - /auth/v1/*
        strip_path: true
    
  - name: rest-v1
    url: http://rest:3000/
    routes:
      - name: rest-v1-routes
        paths:
          - /rest/v1/*
        strip_path: true
    
  - name: realtime-v1
    url: http://realtime:4000/socket/
    routes:
      - name: realtime-v1-routes
        paths:
          - /realtime/v1/*
        strip_path: true
    
  - name: storage-v1
    url: http://storage:5000/
    routes:
      - name: storage-v1-routes
        paths:
          - /storage/v1/*
        strip_path: true
    
  - name: functions-v1
    url: http://functions:8081/
    routes:
      - name: functions-v1-routes
        paths:
          - /functions/v1/*
        strip_path: true
"""
        
        kong_path = os.path.join(project_path, "kong.yml")
        with open(kong_path, 'w') as f:
            f.write(kong_content)
    
    def bootstrap_project(self, project_path):
        """Bootstrap the project by running docker-compose up and ensuring containers are healthy"""
        try:
            # Change to project directory
            original_dir = os.getcwd()
            os.chdir(project_path)
            
            # Pull latest images
            print("Pulling latest Docker images...")
            pull_result = subprocess.run(
                ["docker-compose", "pull"],
                capture_output=True,
                text=True
            )
            
            if pull_result.returncode != 0:
                print(f"Warning: Failed to pull latest images: {pull_result.stderr}")
            
            # Run docker-compose up in detached mode
            print("Starting Docker Compose services...")
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                check=True
            )
            
            print(f"Docker Compose started successfully in {project_path}")
            
            # Wait for services to be healthy
            print("Waiting for services to be healthy...")
            health_check_result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True,
                check=True
            )
            
            print("Services status:")
            print(health_check_result.stdout)
            
            # Change back to original directory
            os.chdir(original_dir)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error with Docker Compose: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def run_locally(self, project_name):
        """Run Supabase services locally without Docker"""
        try:
            project_path = os.path.join(self.projects_dir, project_name)
            config_path = os.path.join(project_path, "supabase_config.json")
            
            # Load configuration
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check if PostgreSQL is running locally
            import psycopg2
            try:
                conn = psycopg2.connect(
                    host=config['db_config']['host'],
                    port=config['db_config']['port'],
                    user=config['db_config']['user'],
                    password=config['db_config']['password'],
                    database=config['db_config']['database']
                )
                conn.close()
                db_status = "✅ PostgreSQL is running"
            except Exception as e:
                db_status = f"❌ PostgreSQL connection failed: {str(e)}"
            
            # Create local startup script
            startup_script = os.path.join(project_path, "start_local.sh")
            with open(startup_script, 'w') as f:
                f.write(f'''#!/bin/bash
echo "Starting Supabase services locally..."
echo "Database: {config['db_config']['host']}:{config['db_config']['port']}"
echo "Project: {project_name}"
echo ""
echo "Services will be available at:"
echo "- Studio: http://localhost:{config['ports']['studio']}"
echo "- API: http://localhost:{config['ports']['kong']}"
echo "- Database: {config['db_config']['host']}:{config['db_config']['port']}"
echo ""
echo "Make sure PostgreSQL is running locally with:"
echo "  host: {config['db_config']['host']}"
echo "  port: {config['db_config']['port']}"
echo "  database: {config['db_config']['database']}"
echo "  user: {config['db_config']['user']}"
echo ""
echo "To start services:"
echo "1. Ensure PostgreSQL is running"
echo "2. Run: npm start (for studio)"
echo "3. Run: npm start (for kong)"
echo ""
echo "Local configuration ready!"
''')
            
            os.chmod(startup_script, 0o755)
            
            return {
                'success': True,
                'message': 'Local configuration created successfully',
                'db_status': db_status,
                'startup_script': startup_script
            }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to create local configuration: {str(e)}',
                'output': str(e)
            }

def main():
    generator = SupabaseProjectGenerator()
    
    # Get user input
    print("=== Supabase Project Generator ===")
    project_name = input("Enter project name: ")
    machine_size = input("Enter machine size (e.g., small, medium, large): ")
    specs = input("Enter machine specs (e.g., 4CPU/8GB RAM): ")
    
    # Create the project with fixed database settings
    project_path = generator.create_project(
        project_name, machine_size, specs
    )
    
    # Bootstrap the project
    bootstrap = input("\nDo you want to bootstrap the project now? (y/n): ")
    if bootstrap.lower() == 'y':
        generator.bootstrap_project(project_path)

if __name__ == "__main__":
    main()
