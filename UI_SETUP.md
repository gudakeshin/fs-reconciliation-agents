# UI Setup Guide

This guide explains how to set up and run the FS Reconciliation Agents UI with the new navigation, log viewer, and agent flow components.

## Features Added

### 1. Main Navigation
- **Left-side navigation drawer** that's common across all pages
- **Dark theme** with professional styling
- **System status indicator** showing online/offline status
- **User profile section** with logout functionality
- **Navigation items**: Dashboard, Data Upload, Exception Management, Reports, Settings, Help

### 2. Log Viewer Component
- **System logs tab**: Shows real-time system logs with filtering
- **Audit trail tab**: Displays audit trail entries with detailed information
- **Advanced filtering**: By level, component, action type, severity, user, entity type, time range
- **Expandable rows**: Click to see detailed information including stack traces, error messages, and additional data
- **Real-time updates**: Auto-refresh every 30 seconds
- **Pagination**: Handle large volumes of log data efficiently

### 3. Agent Flow Component
- **Visual timeline**: Shows the control flow across agents with timeline visualization
- **Agent status dashboard**: Real-time status of all agents (active, idle, inactive)
- **Flow statistics**: Success rates, processing times, step counts
- **Expandable flows**: Click to see detailed flow information
- **Auto-refresh**: Updates every 10 seconds for agent status, 5 seconds for flow data
- **Session-based grouping**: Groups agent actions by session for better organization

## Setup Instructions

### 1. Install Dependencies

```bash
# Install UI dependencies
cd src/ui
npm install

# Install backend dependencies (if not already done)
cd ../..
pip install -r requirements.txt
```

### 2. Set Up Database

Make sure your PostgreSQL database is running and the tables are created:

```bash
# Run database migrations
alembic upgrade head

# Generate sample data (optional but recommended for testing)
python scripts/generate_sample_logs.py
```

### 3. Start the Backend API

```bash
# Start the FastAPI backend
cd src/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start the UI

```bash
# In a new terminal, start the React UI
cd src/ui
npm start
```

The UI will be available at `http://localhost:3000`

## API Endpoints

The UI connects to these backend endpoints:

### Logs and Monitoring
- `GET /api/v1/logs/system` - System logs with filtering
- `GET /api/v1/logs/audit` - Audit trail entries
- `GET /api/v1/logs/agents/flow` - Agent flow information
- `GET /api/v1/logs/agents/status` - Agent status
- `GET /api/v1/logs/statistics` - Log statistics

### Data Upload
- `POST /api/v1/upload/data/upload` - Upload files
- `GET /api/v1/upload/data/upload/status` - Upload status
- `GET /api/v1/upload/data/supported-formats` - Supported file formats

## Usage

### Data Upload Page

1. **Upload Files Tab**: Drag and drop files or click to select
2. **System Logs Tab**: View real-time system logs with filtering options
3. **Audit Trail Tab**: View audit trail entries with detailed information
4. **Agent Flow Tab**: Monitor agent flow control and status

### Navigation

- **Dashboard**: Overview of the system
- **Data Upload**: File upload with monitoring tabs
- **Exception Management**: Handle reconciliation exceptions
- **Reports**: Generate and view reports
- **Settings**: System configuration
- **Help**: Documentation and support

## Features

### Log Viewer Features
- **Real-time filtering**: Filter by log level, component, time range
- **Expandable details**: Click any log entry to see full details
- **Error highlighting**: Errors and warnings are clearly marked
- **Performance metrics**: Execution time, memory usage, CPU usage
- **Auto-refresh**: Automatically updates every 30 seconds

### Agent Flow Features
- **Visual timeline**: Timeline view of agent actions
- **Status indicators**: Color-coded success/failure status
- **Performance metrics**: Processing times, success rates
- **AI model tracking**: Shows which AI models were used
- **Confidence scores**: AI confidence levels for decisions

### Navigation Features
- **Responsive design**: Works on desktop and mobile
- **Active state**: Current page is highlighted
- **System status**: Shows if the system is online
- **User context**: Shows current user information
- **Notifications**: Placeholder for system notifications

## Troubleshooting

### Common Issues

1. **API Connection Error**
   - Ensure the backend is running on port 8000
   - Check that the proxy configuration is correct
   - Verify the API endpoints are accessible

2. **No Log Data**
   - Run the sample data generator: `python scripts/generate_sample_logs.py`
   - Check that the database tables exist
   - Verify the database connection

3. **UI Not Loading**
   - Check that all dependencies are installed
   - Clear browser cache
   - Check browser console for errors

### Development

For development, you can:

1. **Modify the proxy configuration** in `src/ui/setupProxy.js`
2. **Add new API endpoints** in the backend routers
3. **Customize the UI components** in the `src/ui/src/components` directory
4. **Update the navigation** in `src/ui/src/components/Navigation/Navigation.tsx`

## Data Flow

1. **File Upload**: Files are uploaded through the UI
2. **Agent Processing**: Backend agents process the files
3. **Log Generation**: System logs and audit trails are created
4. **UI Monitoring**: The UI displays real-time logs and agent flow
5. **User Interaction**: Users can filter, expand, and monitor the system

This setup provides a comprehensive monitoring and management interface for the FS Reconciliation Agents system with real-time data from the backend.
