#!/usr/bin/env python3
"""
Supabase Project Generator CLI Interface
Provides command-line interface for creating and managing Supabase projects
"""

import sys
import os
import argparse
import json
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.main import SupabaseProjectGenerator


class SupabaseCLI:
    """Command-line interface for Supabase Project Generator"""
    
    def __init__(self):
        self.generator = SupabaseProjectGenerator()
        
    def print_success(self, message):
        """Print success message in green"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
        
    def print_error(self, message):
        """Print error message in red"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
        
    def print_warning(self, message):
        """Print warning message in yellow"""
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
        
    def print_info(self, message):
        """Print info message in blue"""
        print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")

    def create_project(self, args):
        """Create a new Supabase project"""
        try:
            self.print_info(f"Creating Supabase project '{args.name}'...")
            
            # Set default values
            machine_size = args.size or "medium"
            specs = args.specs or "4CPU/8GB RAM"
            db_host = args.db_host or "192.168.1.43"
            db_port = args.db_port or "5432"
            db_user = args.db_user or "postgres"
            db_password = args.db_password or "your_password"
            
            # Create the project
            project_path = self.generator.create_project(
                project_name=args.name,
                machine_size=machine_size,
                specs=specs,
                db_host=db_host,
                db_port=db_port,
                db_user=db_user,
                db_password=db_password
            )
            
            self.print_success(f"Project '{args.name}' created successfully!")
            self.print_info(f"Location: {project_path}")
            
            # Display project info
            config_path = os.path.join(project_path, "supabase_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                print(f"\n{Fore.CYAN}🌐 Access URLs:{Style.RESET_ALL}")
                print(f"  Studio:   http://{config['machine_ip']}:{config['ports']['studio']}")
                print(f"  API:      http://{config['machine_ip']}:{config['ports']['kong']}")
                print(f"  Database: {config['db_config']['host']}:{config['db_config']['port']}")
                
                print(f"\n{Fore.CYAN}🔑 API Keys:{Style.RESET_ALL}")
                print(f"  Anon:     {config['anon_key']}")
                print(f"  Service:  {config['service_key']}")
                
        except Exception as e:
            self.print_error(f"Failed to create project: {str(e)}")
            return 1
        
        return 0

    def list_projects(self, args):
        """List all Supabase projects"""
        try:
            projects_dir = self.generator.projects_dir
            
            if not os.path.exists(projects_dir):
                self.print_info("No projects directory found. No projects created yet.")
                return 0
                
            projects = [d for d in os.listdir(projects_dir) 
                       if os.path.isdir(os.path.join(projects_dir, d))]
            
            if not projects:
                self.print_info("No projects found.")
                return 0
            
            print(f"\n{Fore.CYAN}📋 Supabase Projects:{Style.RESET_ALL}")
            print("-" * 60)
            
            for project in sorted(projects):
                project_path = os.path.join(projects_dir, project)
                config_path = os.path.join(project_path, "supabase_config.json")
                
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        
                        # Check if project is running
                        status = self._check_project_status(project)
                        status_icon = "🟢" if status else "🔴"
                        status_text = "Running" if status else "Stopped"
                        
                        print(f"{status_icon} {project}")
                        print(f"   Size: {config.get('machine_size', 'unknown')}")
                        print(f"   Created: {config.get('created_at', 'unknown')}")
                        print(f"   Status: {status_text}")
                        print(f"   Studio: http://{config['machine_ip']}:{config['ports']['studio']}")
                        print()
                        
                    except Exception:
                        print(f"⚠️  {project} (config error)")
                        print()
                else:
                    print(f"⚠️  {project} (no config)")
                    print()
                    
        except Exception as e:
            self.print_error(f"Failed to list projects: {str(e)}")
            return 1
            
        return 0

    def start_project(self, args):
        """Start a Supabase project"""
        try:
            self.print_info(f"Starting project '{args.name}'...")
            
            success, stdout, stderr = self.generator.start_project(args.name)
            
            if success:
                self.print_success(f"Project '{args.name}' started successfully!")
                
                # Show project URLs
                project_path = os.path.join(self.generator.projects_dir, args.name)
                config_path = os.path.join(project_path, "supabase_config.json")
                
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    print(f"\n{Fore.CYAN}🌐 Access URLs:{Style.RESET_ALL}")
                    print(f"  Studio: http://{config['machine_ip']}:{config['ports']['studio']}")
                    print(f"  API:    http://{config['machine_ip']}:{config['ports']['kong']}")
                    
            else:
                self.print_error(f"Failed to start project '{args.name}'")
                if stderr:
                    print(f"Error: {stderr}")
                return 1
                
        except Exception as e:
            self.print_error(f"Failed to start project: {str(e)}")
            return 1
            
        return 0

    def stop_project(self, args):
        """Stop a Supabase project"""
        try:
            self.print_info(f"Stopping project '{args.name}'...")
            
            success, stdout, stderr = self.generator.stop_project(args.name)
            
            if success:
                self.print_success(f"Project '{args.name}' stopped successfully!")
            else:
                self.print_error(f"Failed to stop project '{args.name}'")
                if stderr:
                    print(f"Error: {stderr}")
                return 1
                
        except Exception as e:
            self.print_error(f"Failed to stop project: {str(e)}")
            return 1
            
        return 0

    def delete_project(self, args):
        """Delete a Supabase project"""
        try:
            # Confirm deletion
            if not args.force:
                response = input(f"Are you sure you want to delete project '{args.name}'? [y/N]: ")
                if response.lower() not in ['y', 'yes']:
                    self.print_info("Deletion cancelled.")
                    return 0
            
            self.print_info(f"Deleting project '{args.name}'...")
            
            success, stdout, stderr = self.generator.delete_project(args.name)
            
            if success:
                self.print_success(f"Project '{args.name}' deleted successfully!")
            else:
                self.print_error(f"Failed to delete project '{args.name}'")
                if stderr:
                    print(f"Error: {stderr}")
                return 1
                
        except Exception as e:
            self.print_error(f"Failed to delete project: {str(e)}")
            return 1
            
        return 0

    def status_project(self, args):
        """Show project status"""
        try:
            project_path = os.path.join(self.generator.projects_dir, args.name)
            config_path = os.path.join(project_path, "supabase_config.json")
            
            if not os.path.exists(config_path):
                self.print_error(f"Project '{args.name}' not found")
                return 1
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print(f"\n{Fore.CYAN}📊 Project Status: {args.name}{Style.RESET_ALL}")
            print("-" * 50)
            
            # Check if project is running
            status = self._check_project_status(args.name)
            status_icon = "🟢" if status else "🔴"
            status_text = "Running" if status else "Stopped"
            
            print(f"Status: {status_icon} {status_text}")
            print(f"Size: {config.get('machine_size', 'unknown')}")
            print(f"Specs: {config.get('specs', 'unknown')}")
            print(f"Created: {config.get('created_at', 'unknown')}")
            
            print(f"\n{Fore.CYAN}🌐 Service URLs:{Style.RESET_ALL}")
            for service, port in config['ports'].items():
                print(f"  {service.title()}: http://{config['machine_ip']}:{port}")
            
            print(f"\n{Fore.CYAN}🗄️ Database:{Style.RESET_ALL}")
            print(f"  Host: {config['db_config']['host']}")
            print(f"  Port: {config['db_config']['port']}")
            print(f"  Database: {config['db_config']['database']}")
            print(f"  User: {config['db_config']['user']}")
            
            print(f"\n{Fore.CYAN}🔑 API Keys:{Style.RESET_ALL}")
            print(f"  Anon: {config['anon_key']}")
            print(f"  Service: {config['service_key']}")
            
        except Exception as e:
            self.print_error(f"Failed to get project status: {str(e)}")
            return 1
            
        return 0

    def _check_project_status(self, project_name):
        """Check if a project is currently running"""
        try:
            project_path = os.path.join(self.generator.projects_dir, project_name)
            compose_file = os.path.join(project_path, 'docker-compose.yml')
            
            if not os.path.exists(compose_file):
                return False
            
            # Use docker compose ps to check status
            import subprocess
            result = subprocess.run(
                ['docker', 'compose', 'ps', '--services', '--filter', 'status=running'],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0 and result.stdout.strip()
            
        except Exception:
            return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Supabase Project Generator - Create and manage Supabase projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create --name myapp --size medium
  %(prog)s list
  %(prog)s start myapp
  %(prog)s stop myapp
  %(prog)s status myapp
  %(prog)s delete myapp --force
        """
    )
    
    parser.add_argument('--version', action='version', version='Supabase Project Generator 1.0.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new Supabase project')
    create_parser.add_argument('--name', required=True, help='Project name')
    create_parser.add_argument('--size', choices=['small', 'medium', 'large', 'xlarge'], 
                              default='medium', help='Machine size (default: medium)')
    create_parser.add_argument('--specs', help='Machine specifications (e.g., "4CPU/8GB RAM")')
    create_parser.add_argument('--db-host', help='PostgreSQL host (default: 192.168.1.43)')
    create_parser.add_argument('--db-port', help='PostgreSQL port (default: 5432)')
    create_parser.add_argument('--db-user', help='PostgreSQL user (default: postgres)')
    create_parser.add_argument('--db-password', help='PostgreSQL password')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a project')
    start_parser.add_argument('name', help='Project name')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a project')
    stop_parser.add_argument('name', help='Project name')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a project')
    delete_parser.add_argument('name', help='Project name')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show project status')
    status_parser.add_argument('name', help='Project name')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    cli = SupabaseCLI()
    
    # Execute command
    if args.command == 'create':
        return cli.create_project(args)
    elif args.command == 'list':
        return cli.list_projects(args)
    elif args.command == 'start':
        return cli.start_project(args)
    elif args.command == 'stop':
        return cli.stop_project(args)
    elif args.command == 'delete':
        return cli.delete_project(args)
    elif args.command == 'status':
        return cli.status_project(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())