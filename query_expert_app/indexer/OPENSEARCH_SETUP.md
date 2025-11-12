# 🔍 OpenSearch Setup Guide

The indexer service requires OpenSearch to store and search document embeddings. Here are your options:

## 🚀 **Quick Start (Recommended)**

### **Option 1: Docker Compose (Easiest)**
```powershell
# Navigate to indexer directory
cd query_expert_app/indexer

# Start OpenSearch
docker-compose up -d

# Check if it's running
curl http://localhost:9200
```

### **Option 2: PowerShell Script**
```powershell
# Run the startup script
.\start-opensearch.ps1
```

## 🐳 **Manual Docker Setup**

If you prefer manual Docker commands:

```powershell
# Start OpenSearch
docker run -d \
  --name opensearch-node \
  -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  opensearchproject/opensearch:2.11.0

# Check if it's running
docker ps
curl http://localhost:9200
```

## 📦 **Native Installation (Advanced)**

If you don't want to use Docker:

1. **Download OpenSearch**: https://opensearch.org/downloads.html
2. **Extract** to a folder (e.g., `C:\opensearch`)
3. **Configure** `config/opensearch.yml`:
   ```yaml
   cluster.name: opensearch-cluster
   node.name: opensearch-node1
   discovery.type: single-node
   http.port: 9200
   plugins.security.disabled: true
   ```
4. **Start**: Run `bin\opensearch.bat`

## 🔧 **Troubleshooting**

### **Connection Refused Error**
```
urllib3.exceptions.ProtocolError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Solutions:**
1. **Check if OpenSearch is running**: `curl http://localhost:9200`
2. **Check Docker containers**: `docker ps`
3. **Check logs**: `docker-compose logs opensearch`
4. **Restart OpenSearch**: `docker-compose restart opensearch`

### **Memory Issues**
If OpenSearch fails to start due to memory:
```yaml
# In docker-compose.yml, reduce memory:
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms256m -Xmx256m"
```

### **Port Conflicts**
If port 9200 is already in use:
```powershell
# Check what's using port 9200
netstat -ano | findstr :9200

# Kill the process or change OpenSearch port
```

## ✅ **Verification**

Once OpenSearch is running, verify:

```powershell
# Test connection
curl http://localhost:9200

# Expected response:
{
  "name" : "opensearch-node1",
  "cluster_name" : "opensearch-cluster",
  "version" : {
    "number" : "2.11.0"
  }
}
```

## 🔄 **Restart Indexer Service**

After OpenSearch is running:

```powershell
# Stop the indexer if running
# Restart with proper environment variables
$env:PYTHONPATH="C:\Users\HP\SQL_AGENT\query_expert_app"
cd query_expert_app/indexer
poetry run python main.py
```

## 🎯 **Expected Result**

You should see:
```
✅ Vector database initialized successfully
🚀 Indexer service startup completed
INFO: Uvicorn running on http://localhost:8002
```

Instead of:
```
⚠️ Vector database initialization failed
⚠️ Service will start in limited mode
```

---

## 🆘 **Need Help?**

If you're still having issues:

1. **Check Docker Desktop** is running
2. **Verify ports** 9200 and 9600 are available
3. **Check system resources** (OpenSearch needs ~512MB RAM)
4. **Try the native installation** if Docker issues persist

The indexer service will work once OpenSearch is properly running on localhost:9200! 🚀