# Processing Limits and Shutdown Implementation

## Overview

This document describes the implementation of processing limits and proper shutdown functionality to kill all child processes when the application stops.

## Changes Made

### 1. Background Processor (`services/background_processor.py`)

#### Added Features:

- **Max Rows Limit**: Added `max_rows_limit` property (default: 10,000 rows for testing)
- **Shutdown Event**: Added `_shutdown_event` for graceful shutdown
- **Row Limiting**: Modified processing to respect the max rows limit
- **Shutdown Method**: Added `shutdown()` method to kill all child processes

#### Key Changes:

```python
# Added properties
self.max_rows_limit = 10000  # Limit processing to 10k rows for testing
self._shutdown_event = threading.Event()

# Modified row counting to respect limit
def _count_file_rows(self, file_path: str) -> int:
    # Limits counting to max_rows_limit for testing

# Modified chunk processing to respect limit
for chunk_df in pd.read_csv(file_path, chunksize=self.chunk_size):
    if total_processed >= self.max_rows_limit:
        break  # Stop processing at limit

# Added shutdown method
def shutdown(self):
    # Set shutdown event
    # Cancel all tasks
    # Shutdown thread and process pools
    # Close database engine
```

### 2. Main Application (`main.py`)

#### Enhanced Shutdown Process:

- **Background Processor Shutdown**: Properly shutdown background processor
- **WebSocket Cleanup**: Close all WebSocket connections
- **Database Cleanup**: Close database connections
- **Error Handling**: Graceful error handling during shutdown

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code...
    yield
    # Enhanced shutdown code:
    # 1. Shutdown background processor
    # 2. Close WebSocket connections
    # 3. Close database connections
```

### 3. WebSocket Manager (`websocket_manager.py`)

#### Added Method:

- **Disconnect All**: Added `disconnect_all()` method to clear all connections

```python
def disconnect_all(self):
    """Disconnect all active connections"""
    self.active_connections.clear()
    self.conversation_connections.clear()
```

### 4. Park Management API (`api/park_management.py`)

#### New Endpoints:

- **Set Max Rows Limit**: `POST /api/parks/set-max-rows-limit`
- **Cancel All Tasks**: `POST /api/parks/cancel-all-tasks`

```python
@router.post("/set-max-rows-limit")
async def set_max_rows_limit(limit: int, ...):
    # Set the maximum number of rows to process (Admin only)

@router.post("/cancel-all-tasks")
async def cancel_all_tasks(...):
    # Cancel all active processing tasks (Admin only)
```

### 5. ETL Base Class (`services/etl/base.py`)

#### Added Base Processor:

- **BaseETLProcessor**: Base class for all ETL processors
- **Row Limiting**: Method to limit dataframe rows for testing

```python
class BaseETLProcessor:
    def __init__(self):
        self.max_rows_limit = 10000  # Default limit for testing

    def limit_dataframe_rows(self, df, max_rows: int = None):
        # Limit dataframe to maximum number of rows for testing
```

### 6. Encaissement ETL (`services/etl/encaissement_etl.py`)

#### Updated to Use Base Class:

- **Inheritance**: Now inherits from `BaseETLProcessor`
- **Row Limiting**: Applies row limiting during data ingestion

```python
class EncaissementETL(BaseETLProcessor):
    def __init__(self):
        super().__init__()
        # ... rest of initialization

    def run_etl(self, input_paths: List[Path]) -> ETLResult:
        # ... processing code
        # Limit rows for testing
        combined_df = self.limit_dataframe_rows(combined_df)
```

## Usage

### 1. Setting Processing Limits

```bash
# Set max rows limit to 1000 for testing
curl -X POST "http://localhost:8000/api/parks/set-max-rows-limit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1000}'
```

### 2. Cancelling All Tasks

```bash
# Cancel all active processing tasks
curl -X POST "http://localhost:8000/api/parks/cancel-all-tasks" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Testing the Implementation

Run the test script:

```bash
python test_processing_limits.py
```

## Benefits

### 1. **Testing Safety**

- Processing is limited to 10,000 rows by default
- Prevents accidental processing of large datasets during testing
- Configurable limit via API endpoint

### 2. **Proper Shutdown**

- All child processes are killed when application stops
- Thread pools and process pools are properly shutdown
- Database connections are closed
- WebSocket connections are cleaned up

### 3. **Task Management**

- Ability to cancel all active processing tasks
- Graceful handling of cancelled tasks
- Progress tracking respects the row limits

### 4. **Resource Management**

- Prevents memory issues with large datasets
- Controlled resource usage during testing
- Proper cleanup of resources

## Configuration

### Default Settings:

- **Max Rows Limit**: 10,000 rows
- **Chunk Size**: 100,000 rows (for reading files)
- **Batch Size**: 10,000 rows (for processing)
- **Thread Pool**: Up to 32 workers
- **Process Pool**: Up to 4 workers

### Environment Variables:

- `MAX_ROWS_LIMIT`: Override default limit (optional)
- `CHUNK_SIZE`: Override default chunk size (optional)
- `BATCH_SIZE`: Override default batch size (optional)

## Monitoring

### Log Messages:

- Row limiting: `"Limiting row count to {limit} for testing"`
- Shutdown: `"Shutting down background processor..."`
- Task cancellation: `"Cancelled {count} tasks"`

### API Responses:

- Set limit: `{"success": true, "message": "Max rows limit set to {limit}", "limit": {limit}}`
- Cancel tasks: `{"success": true, "message": "Cancelled {count} tasks", "cancelled_count": {count}}`

## Future Enhancements

1. **Dynamic Limits**: Allow per-user or per-session limits
2. **Progress Persistence**: Save progress to database for recovery
3. **Resource Monitoring**: Monitor memory and CPU usage
4. **Queue Management**: Implement task queuing system
5. **Retry Logic**: Add retry mechanism for failed tasks

## Troubleshooting

### Common Issues:

1. **Tasks Not Cancelling**: Check if tasks are properly checking the cancelled flag
2. **Memory Issues**: Reduce chunk_size and batch_size
3. **Slow Processing**: Increase max_workers or reduce max_rows_limit
4. **Database Locks**: Ensure proper connection cleanup

### Debug Commands:

```bash
# Check active tasks
curl -X GET "http://localhost:8000/api/parks/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check current limit
curl -X GET "http://localhost:8000/api/parks/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This implementation provides a robust foundation for testing and production use with proper resource management and shutdown procedures.

