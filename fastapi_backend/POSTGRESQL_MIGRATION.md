# PostgreSQL Migration Guide

This guide will help you migrate your FastAPI backend from SQLite to PostgreSQL.

## Prerequisites

1. **Install PostgreSQL** on your system:

   - **Windows**: Download from https://www.postgresql.org/download/windows/
   - **macOS**: `brew install postgresql`
   - **Ubuntu/Debian**: `sudo apt-get install postgresql postgresql-contrib`

2. **Start PostgreSQL service**:

   - **Windows**: PostgreSQL service should start automatically
   - **macOS**: `brew services start postgresql`
   - **Ubuntu/Debian**: `sudo systemctl start postgresql`

3. **Verify PostgreSQL is running**:
   ```bash
   psql --version
   ```

## Migration Steps

### Step 1: Install PostgreSQL Dependencies

```bash
cd fastapi_backend
pip install -r requirements.txt
```

### Step 2: Setup PostgreSQL Database

Run the setup script to create the database:

```bash
python setup_postgresql.py
```

This script will:

- Create the `youcef_db` database
- Test the connection
- Create a `.env` file with PostgreSQL configuration

### Step 3: Migrate Data (Optional)

If you have existing data in your SQLite database that you want to preserve:

```bash
python migrate_to_postgresql.py
```

This script will:

- Read all tables from your SQLite database
- Create corresponding tables in PostgreSQL
- Transfer all data to PostgreSQL

### Step 4: Update Configuration

The configuration has been updated to use PostgreSQL by default. The database URL is now:

```
postgresql://postgres:password@localhost:5432/youcef_db
```

### Step 5: Test the Application

Start your FastAPI server:

```bash
python main.py
```

Visit `http://localhost:8000/docs` to test the API.

## Configuration Options

### Database Connection String Format

```
postgresql://username:password@host:port/database_name
```

### Environment Variables

You can override the database configuration using environment variables:

```bash
export DATABASE_URL="postgresql://your_user:your_password@localhost:5432/youcef_db"
```

### Common PostgreSQL Connection Issues

1. **Connection Refused**:

   - Make sure PostgreSQL is running
   - Check if the port 5432 is correct
   - Verify firewall settings

2. **Authentication Failed**:

   - Check username and password
   - Verify pg_hba.conf configuration
   - Try connecting with `psql` command line tool

3. **Database Does Not Exist**:
   - Run the setup script: `python setup_postgresql.py`
   - Or create manually: `createdb youcef_db`

## PostgreSQL vs SQLite Differences

### Advantages of PostgreSQL:

1. **Better Performance**: Optimized for concurrent access
2. **Advanced Features**: JSON support, full-text search, etc.
3. **Scalability**: Can handle large datasets and high traffic
4. **ACID Compliance**: Better transaction support
5. **Extensibility**: Custom functions and data types

### Configuration Changes Made:

1. **Connection Pooling**: Added `pool_pre_ping=True` and `pool_recycle=300`
2. **Dependencies**: Added `psycopg2-binary` and `asyncpg`
3. **Database URL**: Changed from SQLite to PostgreSQL format

## Troubleshooting

### Common Issues:

1. **ModuleNotFoundError: No module named 'psycopg2'**:

   ```bash
   pip install psycopg2-binary
   ```

2. **Connection timeout**:

   - Check if PostgreSQL is running
   - Verify network connectivity
   - Check firewall settings

3. **Permission denied**:
   - Check PostgreSQL user permissions
   - Verify database ownership

### Debugging Connection Issues:

```python
import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='youcef_db',
        user='postgres',
        password='password'
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

## Performance Optimization

### PostgreSQL-specific optimizations:

1. **Connection Pooling**: Already configured in the connection
2. **Indexes**: Consider adding indexes for frequently queried columns
3. **Query Optimization**: Use EXPLAIN ANALYZE for slow queries
4. **Vacuum**: Regular maintenance with VACUUM and ANALYZE

### Monitoring:

```sql
-- Check active connections
SELECT * FROM pg_stat_activity;

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public';
```

## Backup and Restore

### Backup:

```bash
pg_dump youcef_db > backup.sql
```

### Restore:

```bash
psql youcef_db < backup.sql
```

## Next Steps

After successful migration:

1. **Test all endpoints** to ensure functionality
2. **Monitor performance** and adjust as needed
3. **Set up regular backups**
4. **Configure production settings** (disable DEBUG, set proper SECRET_KEY)
5. **Update deployment scripts** if using containers

## Support

If you encounter issues:

1. Check the logs in `fastapi.log`
2. Verify PostgreSQL is running: `pg_ctl status`
3. Test connection manually with `psql`
4. Check PostgreSQL logs for errors

For more information, refer to:

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Guide](https://docs.sqlalchemy.org/en/14/dialects/postgresql.html)
- [FastAPI Database Documentation](https://fastapi.tiangolo.com/tutorial/sql-databases/)
