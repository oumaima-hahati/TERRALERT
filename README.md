# TERRALERT

**AI-Powered Multi-Hazard Risk Assessment and Early-Warning Platform**

TERRALERT is a geospatial platform designed to support natural hazard risk assessment and, eventually, predictive early warnings in 11 communes of the Tangier–Assilah area, Morocco.

The project combines Geographic Information Systems (GIS), remote sensing, meteorological data, and machine learning.

## 1. Technologies

| Component | Technology |
|---|---|
| Frontend | React + Vite |
| Interactive maps | Leaflet |
| Backend | Python + FastAPI |
| Database (planned integration) | PostgreSQL + PostGIS |
| GIS processing | QGIS + Python |
| Machine learning | Python |

## 2. Project Structure

```text
TERRALERT/
├── frontend/          # React frontend
├── backend/           # FastAPI backend
├── database/          # Database-related files
├── gis/               # GIS processing scripts
├── ml/                # Machine-learning code
├── docs/              # Documentation
├── .gitignore
└── README.md
```

## 3. First-Time Setup

Follow these instructions when running TERRALERT on a new computer for the first time.

### Prerequisites

Make sure the following are installed:

- Git
- Python 3.11 or newer
- Node.js (compatible LTS version)
- npm

### A. Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/YOUR_USERNAME/TERRALERT.git
cd TERRALERT
```

Replace `YOUR_USERNAME` with the repository owner's GitHub username.

### B. Set Up the Backend

Open a terminal in the TERRALERT project directory.

```bash
cd backend
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it (Ubuntu/Linux):

```bash
source .venv/bin/activate
```

Install the required Python libraries:

```bash
python -m pip install -r requirements.txt
```

Start the backend server:

```bash
uvicorn app.main:app --reload
```

The backend runs at:

http://localhost:8000

API documentation:

http://localhost:8000/docs

Health check:

http://localhost:8000/api/health

Expected health response:

```json
{
  "status": "ok",
  "service": "terralert-api"
}
```

**Keep this terminal open while using the application.**

### C. Set Up the Frontend

Open a second terminal in the TERRALERT project directory.

```bash
cd frontend
```

Install the required JavaScript dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

Open the application in your browser:

http://localhost:5173

Both the frontend and backend must be running to use the complete application.

## 4. Daily Use — After the First Installation

You do not need to reinstall the dependencies every time.

### Terminal 1 — Backend

From the TERRALERT project root:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Terminal 2 — Frontend

From the TERRALERT project root:

```bash
cd frontend
npm run dev
```

Open:

http://localhost:5173

**Important:** Run `npm install` again if frontend dependencies change, and reinstall backend requirements if `requirements.txt` changes.

## 5. Stopping the Application

In each terminal, press:

`Ctrl + C`

This stops the frontend or backend server.

The next time you want to use TERRALERT, simply follow Section 4.

## 6. GitHub Collaboration

The project uses GitHub for version control and team collaboration.

Main branches:

- `main`: Stable project version
- `feature/frontend`: Frontend development
- `feature/backend`: Backend development
- `feature/gis`: GIS development
- `feature/ml`: Machine-learning development

Development changes should be submitted through pull requests before being merged into `main`.

## 7. Current Development Status

Implemented:

- React frontend initialized
- Leaflet interactive map working
- FastAPI backend initialized
- API health endpoint working
- Frontend requests reaching the backend

Pending:

- Integration of the validated 11-commune GeoJSON
- PostgreSQL/PostGIS database configuration and integration
- Historical hazard datasets
- Machine-learning models
- Predictive alerts
- Complete dashboard functionality

**Note:** The `/api/communes` endpoint may return a 404 until the validated commune GeoJSON is added. This does not prevent the initial frontend/backend setup from running.

## 8. Development Notes

- Python virtual environments and `node_modules` must not be committed.
- Never commit passwords, API keys or sensitive configuration.
- Large GIS datasets should be stored separately from the source code.
- This is an initial development prototype, not yet an operational early-warning system.

## Development Environment Setup

TERRALERT uses:

- **React + Vite** for the frontend
- **Leaflet** for interactive maps
- **Python + FastAPI** for the backend
- **PostgreSQL 17 + PostGIS 3.5** for spatial data storage
- **Docker Compose** to manage the development database

The database currently runs independently of the backend. FastAPI–PostGIS integration will be implemented in a later development task.

### 1. First-Time Setup

Follow these instructions when running TERRALERT on a new computer.

#### Prerequisites

Install the following software:

- Git
- Python 3.11 or newer
- Node.js and npm (compatible with the project's Vite version)
- Docker Engine
- Docker Compose plugin

Docker installation instructions for Ubuntu:

https://docs.docker.com/engine/install/ubuntu/

#### Clone the repository

```bash
git clone https://github.com/oumaima-hahati/TERRALERT.git
cd TERRALERT
```

#### Set up the database

Create your local environment file:

```bash
cp .env.example .env
```

If `.env.example` is not present, create `.env` manually in the project root:

```dotenv
POSTGRES_PASSWORD=REPLACE_WITH_YOUR_OWN_STRONG_PASSWORD
```

Replace the placeholder with a strong password.

Never commit `.env` to GitHub.

Start PostgreSQL + PostGIS:

```bash
sudo docker compose up -d
```

Check its status:

```bash
sudo docker compose ps
```

The `db` service should show `healthy`.

Verify PostGIS:

```bash
sudo docker compose exec db psql -U terralert -d terralert -c "SELECT PostGIS_Version();"
```

Expected: a version string beginning with `3.5`.

Database connection settings:

| Parameter | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `5432` |
| Database | `terralert` |
| Username | `terralert` |
| Password | Value configured in `.env` |

#### Set up the backend

Open a terminal in the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL:

http://localhost:8000

FastAPI documentation:

http://localhost:8000/docs

Health endpoint:

http://localhost:8000/api/health

Keep this terminal running.

#### Set up the frontend

Open a second terminal in the project root:

```bash
cd frontend
npm ci
npm run dev
```

Frontend URL:

http://localhost:5173

The frontend displays the initial TERRALERT interface and interactive Leaflet map.

The commune GeoJSON and hazard models are integrated separately.

### 2. Daily Startup

After the first installation, you do not need to reinstall dependencies.

#### Start the database

From the TERRALERT project root:

```bash
sudo docker compose up -d
```

#### Start the backend

Open Terminal 1:

```bash
cd ~/Desktop/TERRALERT/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

If your repository is located somewhere else, adjust the path.

#### Start the frontend

Open Terminal 2:

```bash
cd ~/Desktop/TERRALERT/frontend
npm run dev
```

Open the application:

http://localhost:5173

### 3. Stop the Application

Stop the frontend and backend using `Ctrl + C` in their respective terminals.

Stop the database from the project root:

```bash
sudo docker compose stop
```

To start it again:

```bash
sudo docker compose up -d
```

**Warning:** Do not run `docker compose down -v` unless you deliberately intend to delete the database volume and its stored data.

### 4. Troubleshooting

**Docker permission denied**

Use `sudo docker compose` as described above.

**Database is not healthy**

```bash
sudo docker compose ps
sudo docker compose logs db
```

**Frontend dependencies are missing**

```bash
cd frontend
npm ci
```

**Python dependencies are missing**

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Port 5432 already in use**

Another local PostgreSQL service or container may be using the port. Check the port before changing Docker Compose configuration.

**Missing POSTGRES_PASSWORD**

Check that `.env` exists in the project root and contains a nonempty `POSTGRES_PASSWORD` value.

### 5. GitHub Collaboration

The `main` branch contains the shared project version.

For new development work:

1. Update `main` with the latest changes.
2. Create a short-lived feature branch from `main`.
3. Implement and test the changes locally.
4. Commit and push the branch.
5. Create a pull request to merge the changes into `main`.

Do not commit API keys, database passwords, Python virtual environments, `node_modules`, or local database files.

### 6. Current Development Status

**Implemented and tested locally:**

- React/Vite frontend
- Leaflet map
- FastAPI backend
- `/api/health` endpoint
- PostgreSQL 17 and PostGIS 3.5 database environment
- Docker Compose database configuration

**Pending integration:**

- FastAPI connection to PostgreSQL/PostGIS
- Commune GeoJSON and spatial tables
- River and drainage datasets
- Population and exposure datasets
- Hazard-prediction models
- Operational alert functionality

TERRALERT is currently a development prototype, not an operational early-warning system.