import subprocess
import json
import logging
import os
from typing import List, Optional, Dict, Any
from mcp.server.fastapi import FastMCP
from elasticsearch import AsyncElasticsearch

# Initialize FastMCP Server
mcp = FastMCP("Elastic-GenAI-SOC MCP")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
def get_env_var(key: str, default: Any = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value

ELASTIC_URL = get_env_var("ELASTIC_URL", "https://localhost:9200")
ELASTIC_USER = get_env_var("ELASTIC_USER", "elastic")
ELASTIC_PASSWORD = get_env_var("ELASTIC_PASSWORD", "changeme")
VERIFY_CERTS = get_env_var("VERIFY_CERTS", "false").lower() == "true"


# Global Elastic Client
es_client: Optional[AsyncElasticsearch] = None

@mcp.lifespan_context
async def lifespan(server: FastMCP):
    """Manage the lifecycle of the Elastic Client."""
    global es_client
    logger.info(f"Connecting to Elasticsearch at {ELASTIC_URL}...")
    try:
        es_client = AsyncElasticsearch(
            ELASTIC_URL,
            basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD),
            verify_certs=VERIFY_CERTS,
            ca_certs=None if not VERIFY_CERTS else "/path/to/ca.crt"
        )
        info = await es_client.info()
        logger.info(f"Connected to Elastic: {info['version']['number']}")
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        es_client = None # Ensure client is explicitly None on failure
    
    yield
    
    if es_client:
        await es_client.close()

@mcp.tool()
async def health_check() -> str:
    """Returns the health status of the MCP server and Elastic connection."""
    elastic_status = "Connected" if es_client else "Disconnected"
    return json.dumps({
        "status": "running",
        "elastic_connection": elastic_status
    }, indent=2)

# --- Windows Defender Tools ---

def run_powershell_command(cmd: str) -> dict:
    """Executes a PowerShell command and returns the output as a dictionary."""
    try:
        # Construct the full command to return JSON
        full_command = f"powershell -Command \"{cmd} | ConvertTo-Json -Depth 2\""
        
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            shell=True
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {result.stderr}")
            return {"error": result.stderr}
            
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
             return {"output": result.stdout}

    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_defender_status() -> str:
    """
    Get the current status of Windows Defender.
    Returns: Realtime protection status, antivirus status, and update timestamps.
    """
    cmd = "Get-MpComputerStatus"
    data = run_powershell_command(cmd)
    
    if "error" in data:
        return f"Error getting status: {data['error']}"
        
    # Simplify output for LLM consumption
    status_summary = {
        "RealTimeProtectionEnabled": data.get("RealTimeProtectionEnabled"),
        "AntivirusEnabled": data.get("AntivirusEnabled"),
        "AMServiceEnabled": data.get("AMServiceEnabled"),
        "AntispywareEnabled": data.get("AntispywareEnabled"),
        "BehaviorMonitorEnabled": data.get("BehaviorMonitorEnabled"),
        "QuickScanAge": data.get("QuickScanAge"),
        "FullScanAge": data.get("FullScanAge"),
        "AntivirusSignatureLastUpdated": data.get("AntivirusSignatureLastUpdated")
    }
    
    return json.dumps(status_summary, indent=2)

@mcp.tool()
def start_quick_scan() -> str:
    """
    Triggers a Quick Scan using Windows Defender.
    """
    cmd = "Start-MpScan -ScanType QuickScan"
    try:
        subprocess.run(["powershell", "-Command", cmd], check=True, shell=True)
        return "Quick Scan initiated successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to start Quick Scan: {e}"

@mcp.tool()
def start_full_scan() -> str:
    """
    Triggers a Full Scan using Windows Defender.
    Note: This may take a long time and consume significant system resources.
    """
    cmd = "Start-MpScan -ScanType FullScan"
    try:
        subprocess.run(["powershell", "-Command", cmd], check=True, shell=True)
        return "Full Scan initiated successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to start Full Scan: {e}"

# --- Elasticsearch Tools ---

@mcp.tool()
async def get_recent_alerts(limit: int = 5) -> str:
    """
    Fetches the most recent security alerts from Elasticsearch.
    Args:
        limit: Number of alerts to retrieve (default: 5)
    """
    if not es_client:
        return "Elasticsearch client is not connected."

    try:
        resp = await es_client.search(
            index=".alerts-security.alerts-*",
            sort=[{"@timestamp": {"order": "desc"}}],
            size=limit,
            source=["@timestamp", "kibana.alert.rule.name", "event.action", "host.name", "message"]
        )
        
        alerts = []
        for hit in resp['hits']['hits']:
            source = hit['_source']
            alerts.append({
                "time": source.get("@timestamp"),
                "rule": source.get("kibana", {}).get("alert", {}).get("rule", {}).get("name"),
                "action": source.get("event", {}).get("action"),
                "host": source.get("host", {}).get("name"),
                "message": source.get("message")
            })
            
        if not alerts:
            return "No recent alerts found."
            
        return json.dumps(alerts, indent=2)
        
    except Exception as e:
        return f"Failed to query Elastic: {str(e)}"

@mcp.tool()
async def search_logs(query: str, index: str = "logs-*", limit: int = 10) -> str:
    """
    Searches for logs in Elasticsearch using a KQL (Kibana Query Language) or Lucene query string.
    Use this to investigate specific IPs, users, or event IDs found in alerts.
    Args:
        query: The query string (e.g., "process.name: powershell.exe" or "source.ip: 10.0.0.5")
        index: Index pattern to search (default: logs-*)
        limit: Max results (default: 10)
    """
    if not es_client:
        return "Elasticsearch client is not connected."

    try:
        resp = await es_client.search(
            index=index,
            q=query,
            sort=[{"@timestamp": {"order": "desc"}}],
            size=limit
        )
        
        logs = []
        for hit in resp['hits']['hits']:
            logs.append(hit['_source'])
            
        if not logs:
            return f"No logs found for query: {query}"
            
        return json.dumps(logs, indent=2, default=str)

    except Exception as e:
        return f"Search failed: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    # Run the server on localhost:8000
    uvicorn.run(mcp, host="0.0.0.0", port=8000)
