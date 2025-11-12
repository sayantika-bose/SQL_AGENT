# PowerShell script to start OpenSearch for the indexer service

Write-Host "🚀 Starting OpenSearch for Document Indexer..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if OpenSearch is already running
$existing = docker ps -q -f name=opensearch-node
if ($existing) {
    Write-Host "⚠️  OpenSearch container already running" -ForegroundColor Yellow
    Write-Host "🔍 Checking OpenSearch health..."
    
    # Test OpenSearch connection
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9200" -TimeoutSec 5
        Write-Host "✅ OpenSearch is healthy and accessible" -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "⚠️  OpenSearch container exists but not responding. Restarting..." -ForegroundColor Yellow
        docker-compose down
    }
}

# Start OpenSearch with docker-compose
Write-Host "🐳 Starting OpenSearch containers..." -ForegroundColor Blue
docker-compose up -d

# Wait for OpenSearch to be ready
Write-Host "⏳ Waiting for OpenSearch to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

do {
    $attempt++
    Start-Sleep -Seconds 2
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9200" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ OpenSearch is ready!" -ForegroundColor Green
            Write-Host "🌐 OpenSearch URL: http://localhost:9200" -ForegroundColor Cyan
            Write-Host "📊 OpenSearch Dashboards: http://localhost:5601" -ForegroundColor Cyan
            exit 0
        }
    } catch {
        Write-Host "⏳ Attempt $attempt/$maxAttempts - OpenSearch not ready yet..." -ForegroundColor Yellow
    }
} while ($attempt -lt $maxAttempts)

Write-Host "❌ OpenSearch failed to start within timeout" -ForegroundColor Red
Write-Host "🔍 Check logs with: docker-compose logs opensearch" -ForegroundColor Yellow
exit 1