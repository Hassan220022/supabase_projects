# Supabase Project Generator

A web-based interface for creating and managing self-hosted Supabase projects with Docker.

## ✅ Fixed Issues

1. **Port Conflict**: Changed Flask app from port 8000 to 5000 to avoid conflict with Kong
2. **Database Configuration**: Made database settings configurable via environment variables
3. **Missing Imports**: Fixed all missing module imports and added proper error handling
4. **Directory Creation**: Ensured projects directory is created automatically
5. **Template Variables**: Fixed undefined variables in HTML templates
6. **Service Status**: Added proper service status checking
7. **Flash Messages**: Added flash message display in all templates
8. **Missing Methods**: Added missing `run_locally` method
9. **Startup Scripts**: Created automatic startup scripts

## 🚀 Quick Start

### Method 1: Using the Start Script
```bash
cd /workspace
./start.sh
```

### Method 2: Direct Python
```bash
cd /workspace
python3 src/web/web_interface.py
```

### Method 3: Using systemd (for automatic startup)
```bash
sudo cp /workspace/supabase-generator.service /etc/systemd/system/
sudo systemctl enable supabase-generator
sudo systemctl start supabase-generator
```

## 🌐 Access

Once started, access the application at:
- **Web Interface**: http://localhost:5000
- **Default Database**: PostgreSQL at 192.168.1.43:5432

## 🔧 Configuration

Set these environment variables to customize:

```bash
export SUPABASE_DB_HOST=your-db-host      # Default: 192.168.1.43
export SUPABASE_DB_PORT=5432              # Default: 5432
export SUPABASE_DB_USER=postgres          # Default: postgres
export SUPABASE_DB_PASSWORD=your-password # Default: postgres
```

## 📋 Features

- **Create Projects**: Generate new Supabase projects with custom configurations
- **Manage Projects**: Start, stop, and delete existing projects
- **Auto-Start**: Projects automatically start after creation
- **Service Monitoring**: Real-time status checking for all Supabase services
- **Port Management**: Automatic port allocation to avoid conflicts
- **JWT Generation**: Secure JWT token generation for authentication

## 🛠️ Requirements

- Python 3.x
- Docker & Docker Compose
- PostgreSQL (remote or local)

## 📦 Dependencies

All Python dependencies are listed in `/workspace/config/requirements.txt`:
- Flask
- Docker SDK
- PyJWT
- psutil
- psycopg2-binary
- And more...

## 🐛 Troubleshooting

### Port Already in Use
If you see "Port 5000 is in use", either:
1. Kill the existing process: `sudo lsof -ti:5000 | xargs kill -9`
2. Or change the port in `web_interface.py`

### Docker Permission Issues
Run with sudo or add your user to the docker group:
```bash
sudo usermod -aG docker $USER
```

### Database Connection Failed
Check your PostgreSQL is running and accessible:
```bash
psql -h 192.168.1.43 -U postgres -p 5432
```

## 🎯 Usage

1. **Start the application** using any method above
2. **Open your browser** to http://localhost:5000
3. **Create a new project**:
   - Enter project name
   - Select machine size
   - Add optional specifications
   - Click "Create Supabase Project"
4. **Manage projects** from the "My Projects" page

## 🔒 Security Notes

- Default credentials are for development only
- Change JWT secrets in production
- Use strong database passwords
- Consider HTTPS for production deployments