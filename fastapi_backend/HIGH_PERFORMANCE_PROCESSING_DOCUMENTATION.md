# High-Performance Background Processing System

## 🚀 Overview

This document describes the high-performance background processing system designed to handle large Excel files (millions of rows, 43 columns) with multi-threading, bulk operations, and real-time progress tracking.

## 🏗️ Architecture

### Core Components

1. **BackgroundProcessor** - Multi-threaded processing engine
2. **ProcessingWebSocketManager** - Real-time updates via WebSocket
3. **Enhanced API Endpoints** - Background processing endpoints
4. **Frontend Integration** - Real-time progress UI

## ⚡ Performance Features

### Multi-Threading

- **Thread Pool**: Up to 32 workers (configurable)
- **Process Pool**: Up to 4 processes for CPU-intensive tasks
- **Chunk Processing**: Files processed in 100k row chunks
- **Batch Operations**: Database saves in 10k row batches

### Bulk Database Operations

- **Pandas to_sql**: Fastest bulk insert method
- **Connection Pooling**: 20 connections with 30 overflow
- **Batch Commits**: Commits every 1000 records
- **Fallback Strategy**: Individual saves if bulk fails

### Memory Optimization

- **Chunked Reading**: Process large files without loading entirely into memory
- **Streaming Processing**: Process data as it's read
- **Garbage Collection**: Automatic cleanup of processed chunks

## 🔧 API Endpoints

### Background Processing

- `POST /api/parks/process-excel-background` - Start background processing
- `GET /api/parks/processing-status/{task_id}` - Get processing status
- `GET /api/parks/processing-tasks` - Get all active tasks
- `POST /api/parks/cancel-processing/{task_id}` - Cancel processing
- `POST /api/parks/cleanup-tasks` - Clean up old tasks

### WebSocket Endpoints

- `ws://localhost:8000/ws/processing/` - Real-time processing updates

## 📊 Processing Flow

### 1. File Upload

```javascript
// Frontend uploads file
const formData = new FormData();
formData.append("file", file);

const response = await fetch("/api/parks/process-excel-background", {
  method: "POST",
  body: formData,
});
```

### 2. Background Processing

```python
# Backend starts processing
task_id = background_processor.start_processing(
    file_path=tmp_file_path,
    file_id=file_id,
    user_id=user_id
)
```

### 3. Chunk Processing

```python
# Process file in chunks
for chunk_df in pd.read_csv(file_path, chunksize=100000):
    # Apply filtering rules
    processed_df = processor._apply_processing_rules(chunk_df)

    # Bulk save to database
    saved_count = self._bulk_save_parks(processed_df.to_dict('records'))

    # Update progress
    progress = (processed_rows / total_rows) * 100
```

### 4. Real-time Updates

```python
# Send progress updates via WebSocket
await processing_ws_manager.send_task_update(task_id, {
    "progress": progress,
    "status": "processing",
    "processed_rows": processed_rows,
    "statistics": stats
})
```

## 🎯 Performance Metrics

### Expected Performance

- **1M rows, 43 columns**: ~5-10 minutes processing time
- **Memory usage**: <2GB (regardless of file size)
- **Database throughput**: ~50k-100k records/minute
- **Real-time updates**: <100ms latency

### Optimization Features

- **Parallel Processing**: Multiple chunks processed simultaneously
- **Bulk Inserts**: 10x faster than individual inserts
- **Connection Pooling**: Reduced database connection overhead
- **Memory Streaming**: Constant memory usage regardless of file size

## 🔄 Real-time Updates

### WebSocket Connection

```javascript
// Connect to processing updates
const ws = new WebSocket(
  `ws://localhost:8000/ws/processing/?user_id=${userId}&token=${token}`
);

// Subscribe to task updates
ws.send(
  JSON.stringify({
    type: "subscribe_task",
    task_id: taskId,
  })
);

// Receive real-time updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === "processing_update") {
    updateProgress(message.data);
  }
};
```

### Update Types

- **Progress Updates**: Real-time progress percentage
- **Status Changes**: Processing, completed, failed, cancelled
- **Statistics**: Rows processed, filtered, saved
- **Anomalies**: Real-time anomaly detection
- **Errors**: Processing errors and warnings

## 🎨 Frontend Integration

### Processing UI Components

- **Progress Bar**: Real-time progress visualization
- **Status Badge**: Current processing status
- **Statistics Cards**: Live processing statistics
- **Anomaly List**: Real-time anomaly display
- **Connection Status**: WebSocket connection indicator

### User Experience

- **Non-blocking**: Users can navigate away during processing
- **Real-time Feedback**: Live progress and statistics
- **Error Handling**: Clear error messages and recovery options
- **Cancellation**: Ability to cancel long-running processes

## 🛡️ Error Handling

### Processing Errors

- **Chunk-level Recovery**: Failed chunks don't stop entire process
- **Fallback Strategies**: Bulk insert → individual saves
- **Error Logging**: Comprehensive error tracking
- **Graceful Degradation**: Continue processing despite errors

### WebSocket Errors

- **Connection Recovery**: Automatic reconnection attempts
- **Message Validation**: Robust message parsing
- **Error Propagation**: Clear error communication to frontend

## 📈 Monitoring & Logging

### Performance Monitoring

- **Processing Time**: Track processing duration
- **Throughput**: Records processed per minute
- **Memory Usage**: Monitor memory consumption
- **Error Rates**: Track processing success rates

### Logging

- **Structured Logging**: JSON-formatted logs
- **Progress Tracking**: Detailed progress logs
- **Error Logging**: Comprehensive error information
- **Performance Metrics**: Processing statistics

## 🔧 Configuration

### Performance Tuning

```python
# Background processor configuration
background_processor = BackgroundProcessor(
    max_workers=32,  # Thread pool size
    batch_size=10000,  # Database batch size
    chunk_size=100000  # File chunk size
)

# Database connection pool
bulk_engine = create_engine(
    engine.url,
    pool_size=20,      # Connection pool size
    max_overflow=30,   # Additional connections
    pool_pre_ping=True # Connection health checks
)
```

### Environment Variables

- `MAX_WORKERS`: Maximum thread pool size
- `BATCH_SIZE`: Database batch size
- `CHUNK_SIZE`: File processing chunk size
- `DB_POOL_SIZE`: Database connection pool size

## 🚀 Usage Examples

### Start Background Processing

```bash
curl -X POST "http://localhost:8000/api/parks/process-excel-background" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@large_file.csv"
```

### Get Processing Status

```bash
curl "http://localhost:8000/api/parks/processing-status/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cancel Processing

```bash
curl -X POST "http://localhost:8000/api/parks/cancel-processing/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📋 Best Practices

### File Processing

- **Chunk Size**: 100k rows for optimal memory/performance balance
- **Batch Size**: 10k records for database operations
- **Error Handling**: Always implement fallback strategies
- **Progress Updates**: Update progress every chunk completion

### Database Operations

- **Bulk Inserts**: Use pandas to_sql for maximum performance
- **Connection Pooling**: Configure appropriate pool sizes
- **Transaction Management**: Commit in batches to avoid long transactions
- **Index Management**: Ensure proper indexing for large datasets

### WebSocket Management

- **Connection Limits**: Monitor active connections
- **Message Size**: Keep messages under 64KB
- **Error Handling**: Implement robust error recovery
- **Cleanup**: Properly close connections on disconnect

## 🔮 Future Enhancements

### Planned Features

- **Distributed Processing**: Multi-server processing support
- **Queue System**: Redis/RabbitMQ integration
- **Advanced Analytics**: Real-time processing analytics
- **Auto-scaling**: Dynamic worker scaling based on load

### Performance Improvements

- **GPU Acceleration**: CUDA support for data processing
- **Compression**: File compression for faster transfers
- **Caching**: Redis caching for frequently accessed data
- **CDN Integration**: Global file distribution

## 📞 Support

For questions or issues with the high-performance processing system:

- Check logs in `fastapi.log`
- Monitor WebSocket connections
- Review processing statistics
- Contact development team for performance tuning

---

**Note**: This system is designed to handle files with millions of rows efficiently. For optimal performance, ensure adequate server resources (CPU, RAM, disk I/O) are available.

