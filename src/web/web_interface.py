#!/usr/bin/env python3

import sys
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

# Add the parent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Now we can import the SupabaseProjectGenerator
from src.core.main import SupabaseProjectGenerator

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-secret-key-change-in-production'

generator = SupabaseProjectGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_project():
    try:
        # Get form data
        project_name = request.form['project_name']
        machine_size = request.form['machine_size']
        specs = request.form['specs']
        username = request.form.get('username')
        password = request.form.get('password')
        # Use configurable database settings with environment variables fallback
        db_host = os.environ.get('SUPABASE_DB_HOST', '192.168.1.43')
        db_port = os.environ.get('SUPABASE_DB_PORT', '5432')
        db_user = os.environ.get('SUPABASE_DB_USER', 'postgres')
        db_password = os.environ.get('SUPABASE_DB_PASSWORD', 'postgres')
        use_local_db = request.form.get('use_local_db', 'false') == 'true'
        
        # Validate required fields
        if not project_name:
            flash('Project name is required!', 'error')
            return redirect(url_for('index'))
        
        # Create the project
        project_path = generator.create_project(
            project_name=project_name,
            machine_size=machine_size,
            specs=specs,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            username=username,
            password=password,
            use_local_db=use_local_db
        )
        
        # Auto-start the project after creation
        start_result = generator.start_project(project_name)
        
        # Load config to pass to template
        config_path = os.path.join(project_path, 'supabase_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Run locally with PostgreSQL instead of Docker
        local_result = generator.run_locally(project_name)
        
        # Get creation logs
        creation_logs = generator.logger.get_logs()
        
        # Get real service status after docker-compose
        service_status = {}
        ports = config.get('ports', {})
        for service, port in ports.items():
            service_status[service] = generator.get_service_status(port)
        
        flash(f'Project "{project_name}" created and Docker services started at {project_path}', 'success')
        return render_template('success.html', 
                             project_name=project_name, 
                             project_path=project_path, 
                             config=config,
                             creation_logs=creation_logs,
                             service_status=service_status,
                             local_result=local_result)
        
    except Exception as e:
        flash(f'Error creating project: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/projects')
def list_projects():
    projects = []
    if os.path.exists(generator.projects_dir):
        for project_name in os.listdir(generator.projects_dir):
            project_path = os.path.join(generator.projects_dir, project_name)
            if os.path.isdir(project_path):
                config_path = os.path.join(project_path, 'supabase_config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        
                        # Check service status for each port
                        service_status = {}
                        ports = config.get('ports', {})
                        for service, port in ports.items():
                            service_status[service] = generator.get_service_status(port)
                        # Clean created_at (avoid byte-string artifacts like b'...\n')
                        raw_created = config.get('created_at', 'Unknown')
                        if isinstance(raw_created, str):
                            created_at = raw_created.strip()
                            # remove leading b' or b"
                            if created_at.startswith("b'") and created_at.endswith("'"):
                                created_at = created_at[2:].strip("'")
                            elif created_at.startswith('b"') and created_at.endswith('"'):
                                created_at = created_at[2:].strip('"')
                            # strip trailing escaped newlines if present
                            created_at = created_at.replace('\\n', '').strip()
                        else:
                            created_at = str(raw_created)

                        projects.append({
                            'name': project_name,
                            'path': project_path,
                            'created_at': created_at,
                            'machine_size': config.get('machine_size', 'Unknown'),
                            'specs': config.get('specs', 'Unknown'),
                            'machine_ip': config.get('machine_ip', 'Unknown'),
                            'ports': ports,
                            'service_status': service_status
                        })
    return render_template('projects.html', projects=projects)

@app.route('/api/project/<project_name>/status')
def project_status_api(project_name):
    """API endpoint to get real-time project status"""
    try:
        config_path = os.path.join(generator.projects_dir, project_name, 'supabase_config.json')
        if not os.path.exists(config_path):
            return jsonify({'error': 'Project not found'}), 404
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Compute status per port using get_service_status
        ports = config.get('ports', {})
        service_status = {svc: generator.get_service_status(port) for svc, port in ports.items()}
        
        return jsonify({
            'project_name': project_name,
            'status': service_status,
            'ports': ports,
            'machine_ip': config.get('machine_ip')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/project/<project_name>/start', methods=['POST'])
def start_project_api(project_name):
    """API endpoint to start a project"""
    try:
        project_path = os.path.join(generator.projects_dir, project_name)
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        # Use existing generator and capture details
        result = generator.start_project(project_name)
        if isinstance(result, tuple):
            success, out, err = result
        else:
            success, out, err = (bool(result), '', '')

        if success:
            return jsonify({'success': True, 'message': f'Project {project_name} started successfully', 'stdout': out, 'stderr': err})
        else:
            return jsonify({'success': False, 'message': f'Failed to start project {project_name}', 'stdout': out, 'stderr': err})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/project/<project_name>/stop', methods=['POST'])  
def stop_project_api(project_name):
    """API endpoint to stop a project"""
    try:
        project_path = os.path.join(generator.projects_dir, project_name)
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        result = generator.stop_project(project_name)
        if isinstance(result, tuple):
            success, out, err = result
        else:
            success, out, err = (bool(result), '', '')

        if success:
            return jsonify({'success': True, 'message': f'Project {project_name} stopped successfully', 'stdout': out, 'stderr': err})
        else:
            return jsonify({'success': False, 'message': f'Failed to stop project {project_name}', 'stdout': out, 'stderr': err})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/project/<project_name>/delete', methods=['POST'])
def delete_project_api(project_name):
    """API endpoint to delete a project"""
    try:
        project_path = os.path.join(generator.projects_dir, project_name)
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        result = generator.delete_project(project_name)
        if isinstance(result, tuple):
            success, out, err = result
        else:
            success, out, err = (bool(result), '', '')

        if success:
            return jsonify({'success': True, 'message': f'Project {project_name} deleted successfully', 'stdout': out, 'stderr': err})
        else:
            return jsonify({'success': False, 'message': f'Failed to delete project {project_name}', 'stdout': out, 'stderr': err})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/projects/status')
def projects_status_api():
    """API endpoint to check if projects status has changed"""
    try:
        # Simple check - could be enhanced with caching/timestamps
        return jsonify({'should_refresh': True})
    except Exception as e:
        return jsonify({'should_refresh': False, 'error': str(e)})

@app.route('/logs')
def get_logs():
    """Get current creation logs"""
    logs = generator.logger.get_logs()
    return {'logs': logs}

if __name__ == '__main__':
    # Use port 5000 to avoid conflict with Kong service
    app.run(host='0.0.0.0', port=5000, debug=True)
