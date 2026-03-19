# Face Recognition Attendance System

A production-ready, self-hosted face recognition attendance system designed to run on TrueNAS or any Docker-compatible server. All data stays local - no cloud dependencies.

## Features

- **Real-Time Face Recognition**: Automatic face detection and recognition using live camera feed
- **Liveness Detection**: Basic anti-spoofing measures to prevent photo attacks
- **Time In/Out Tracking**: Automatic logging with duplicate prevention
- **Snapshot Evidence**: Each recognition attempt is saved as evidence
- **Automatic Camera Reconnection**: Recovers automatically if camera disconnects
- **Adjustable Confidence Threshold**: Fine-tune recognition sensitivity in settings
- **Clean Modern Interface**: Large camera preview with clear on-screen messages
- **Admin Dashboard**: Overview of today's attendance, quick actions
- **User Management**: Add, edit, delete users and their face registrations
- **Attendance Records**: Filter by date, name, ID, status
- **Excel/CSV Export**: Generate downloadable reports saved to local storage
- **Audit Logging**: Track all admin actions
- **Privacy-Focused**: All data stored locally, no external APIs

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, FastAPI |
| Database | SQLite (PostgreSQL-ready) |
| Face Recognition | dlib / face_recognition |
| Frontend | Server-rendered Jinja2 templates |
| Excel Export | openpyxl |
| Authentication | JWT + bcrypt |
| Containerization | Docker + Docker Compose |

## Project Structure

```
face-attendance-system/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database setup
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── routers/          # API endpoints
│   │   │   ├── auth.py       # Authentication
│   │   │   ├── users.py      # User management
│   │   │   ├── attendance.py # Attendance records
│   │   │   ├── recognition.py # Face recognition
│   │   │   ├── export.py     # Excel/CSV export
│   │   │   └── settings.py   # System settings
│   │   ├── services/         # Business logic
│   │   │   ├── face_recognition_service.py
│   │   │   ├── attendance_service.py
│   │   │   └── export_service.py
│   │   └── utils/            # Utilities
│   │       ├── logging.py
│   │       └── security.py
│   ├── templates/            # HTML templates
│   ├── static/               # CSS, JS
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Database Schema

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| employee_id | VARCHAR(50) | Unique employee identifier |
| name | VARCHAR(100) | Full name |
| department | VARCHAR(100) | Department/class |
| email | VARCHAR(255) | Email address |
| phone | VARCHAR(50) | Phone number |
| is_active | BOOLEAN | Active status |
| face_registered | BOOLEAN | Face registration status |
| face_embedding | BLOB | 128-dim face embedding |
| face_image_path | VARCHAR(500) | Path to face image |
| notes | TEXT | Additional notes |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Update timestamp |

### Attendance Records Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| employee_id | VARCHAR(50) | Employee ID |
| name | VARCHAR(100) | Name at time of record |
| date | VARCHAR(10) | Date (YYYY-MM-DD) |
| time_in | DATETIME | Time in timestamp |
| time_out | DATETIME | Time out timestamp |
| status | VARCHAR(20) | present/completed |
| confidence_score | FLOAT | Recognition confidence |
| is_recognized | BOOLEAN | Was face recognized |
| notes | TEXT | Additional notes |

### Audit Logs Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| timestamp | DATETIME | Action timestamp |
| admin_user | VARCHAR(100) | Admin username |
| action | VARCHAR(50) | Action type |
| resource_type | VARCHAR(50) | Resource affected |
| resource_id | UUID | Resource ID |
| details | JSON | Additional details |
| ip_address | VARCHAR(45) | Client IP |

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 2GB RAM
- Webcam (for live recognition) or images for upload

### 1. Clone and Configure

```bash
# Clone the repository
cd /path/to/your/directory

# Copy environment file
cp .env.example .env

# Edit configuration (IMPORTANT: change SECRET_KEY and passwords!)
nano .env
```

### 2. Build and Run

```bash
# Build the container (first time - may take 10-15 minutes due to dlib compilation)
docker-compose build

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

Open your browser and go to: `http://your-server-ip:8000`

Default credentials:
- Username: `admin`
- Password: `admin123`

**IMPORTANT**: Change these in your `.env` file!

## TrueNAS Deployment

### Using TrueNAS SCALE Apps

1. **Create Dataset for Persistent Storage**
   ```
   Go to: Storage > Pools > [Your Pool] > Add Dataset
   Create datasets for:
   - face-attendance-db
   - face-attendance-images
   - face-attendance-exports
   - face-attendance-logs
   ```

2. **Deploy via Custom App**
   ```
   Go to: Apps > Manage Catalogs > Launch Docker Image

   Image: Build from Dockerfile or use pre-built image
   Port: 8000:8000

   Add Host Path Volumes:
   - /mnt/pool/face-attendance-db -> /app/data/db
   - /mnt/pool/face-attendance-images -> /app/data/faces
   - /mnt/pool/face-attendance-snapshots -> /app/data/snapshots
   - /mnt/pool/face-attendance-exports -> /app/data/exports
   - /mnt/pool/face-attendance-logs -> /app/data/logs

   Environment Variables:
   - SECRET_KEY: your-secure-random-key
   - ADMIN_USERNAME: admin
   - ADMIN_PASSWORD: your-secure-password
   ```

### Using Docker Compose on TrueNAS

1. **SSH into TrueNAS**
   ```bash
   ssh root@truenas-ip
   ```

2. **Create Directory Structure**
   ```bash
   mkdir -p /mnt/pool/docker/face-attendance
   cd /mnt/pool/docker/face-attendance
   ```

3. **Copy Files**
   Transfer all project files to this directory

4. **Update docker-compose.yml for TrueNAS**
   ```yaml
   volumes:
     - /mnt/pool/data/face-db:/app/data/db
     - /mnt/pool/data/face-images:/app/data/faces
     - /mnt/pool/data/face-snapshots:/app/data/snapshots
     - /mnt/pool/data/face-exports:/app/data/exports
     - /mnt/pool/data/face-logs:/app/data/logs
   ```

5. **Build and Run**
   ```bash
   docker-compose up -d --build
   ```

## Usage Guide

### 1. Add Users

1. Go to **Users** page
2. Click **Add User**
3. Fill in:
   - Employee ID (required, unique)
   - Name (required)
   - Department (optional)
   - Email, Phone (optional)
4. Click **Save**

### 2. Register Faces

1. On the **Users** page, find the user
2. Click **Add Face**
3. Upload a clear photo with:
   - Single face visible
   - Good lighting
   - Front-facing
   - At least 100x100 pixels
4. System will extract facial features and store the embedding

### 3. Record Attendance

1. Go to **Recognition** page
2. Select your camera from the dropdown
3. Click **Start Camera**
4. Select **Time In** or **Time Out**
5. System will automatically:
   - Perform liveness detection
   - Detect and recognize faces every 2 seconds
   - Save a snapshot of each attempt
   - Display "Welcome, [Name]" for successful recognition
   - Display "Face not recognized" for failed attempts
   - Record attendance if match found (above threshold)
6. Camera automatically reconnects if disconnected

### 4. Export Reports

1. Go to **Exports** page
2. Select date range
3. Choose format (Excel or CSV)
4. Click **Generate Export**
5. File downloads automatically and saves to server

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| SECRET_KEY | (change me) | JWT secret key |
| ADMIN_USERNAME | admin | Admin login username |
| ADMIN_PASSWORD | admin123 | Admin login password |
| FACE_MATCH_THRESHOLD | 0.6 | Recognition strictness (0.0-1.0) |
| DUPLICATE_TIMEOUT | 30 | Minutes before allowing duplicate entry |
| LOG_LEVEL | INFO | Logging verbosity |

### Face Match Threshold Guide

| Value | Behavior |
|-------|----------|
| 0.4-0.5 | Very lenient, may cause false positives |
| 0.55-0.65 | Recommended for most use cases |
| 0.7-0.8 | Strict, may cause false negatives |
| 0.85+ | Very strict, only near-identical matches |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Admin login |
| POST | /api/auth/logout | Admin logout |
| GET | /api/users | List users |
| POST | /api/users | Create user |
| PUT | /api/users/{id} | Update user |
| DELETE | /api/users/{id} | Delete user |
| POST | /api/users/{id}/register-face | Register face |
| GET | /api/attendance | List attendance |
| GET | /api/attendance/today | Today's attendance |
| POST | /api/recognition/identify | Identify face |
| POST | /api/export/generate | Generate export |

## Privacy & Consent

**IMPORTANT**: This system processes biometric data. Before deployment:

1. **Obtain explicit consent** from all users
2. **Inform users** about:
   - What data is collected (face images, embeddings)
   - How it's stored (locally, encrypted at rest if configured)
   - How long it's retained
   - How to request deletion
3. **Comply with regulations**:
   - GDPR (EU)
   - CCPA (California)
   - BIPA (Illinois)
   - Local biometric privacy laws
4. **Implement data retention policies**
5. **Post visible notices** about biometric collection

## Troubleshooting

### Container won't start
```bash
docker-compose logs face-attendance
```

### Face not detected
- Ensure image has clear, visible face
- Check lighting (avoid harsh shadows)
- Face should be at least 100x100 pixels
- Try different angles

### Low confidence scores
- Register multiple face images per user
- Ensure registration images are high quality
- Adjust FACE_MATCH_THRESHOLD

### Database issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

## Backup & Restore

### Backup
```bash
# Stop container
docker-compose down

# Backup volumes
tar -czvf backup.tar.gz \
  /var/lib/docker/volumes/face-attendance_face_db \
  /var/lib/docker/volumes/face-attendance_face_images \
  /var/lib/docker/volumes/face-attendance_face_exports

# Restart
docker-compose up -d
```

### Restore
```bash
docker-compose down
tar -xzvf backup.tar.gz -C /
docker-compose up -d
```

## License

This project is provided as-is for educational and internal use. Ensure compliance with all applicable laws regarding biometric data processing before deployment.

## Support

For issues and feature requests, please check the logs first:
```bash
docker-compose logs -f
```

Review the log files at `/app/data/logs/` for detailed error information.
