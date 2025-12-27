# Setup Guide

## 1. Infrastructure Setup

### Prerequisites
*   **OS**: Linux (Ubuntu 20.04/22.04 LTS recommended) or Windows with WSL2.
*   **Docker**: Version 24+ installed.
*   **Resources**: Minimum 8GB RAM, 4 vCPUs.

### Deployment Steps
1.  **Navigate**: Go to the `infrastructure` directory.
2.  **Configure**:
    *   Review `infrastructure/config/elasticsearch/elasticsearch.yml`.
    *   Review `infrastructure/config/kibana/kibana.yml`.
3.  **Run**:
    ```bash
    docker-compose up -d
    ```
4.  **Verify**: Access Kibana at `http://localhost:5601`.

## 2. GenAI SOC Setup

### Prerequisites
*   **Python**: Version 3.10 or higher.
*   **API Key**: OpenAI or Anthropic API key for the LLM.

### Installation
1.  **Navigate**: Go to the `genai-soc` directory.
2.  **Environment**: 
    ```bash
    cp .env.example .env
    # Edit .env and add ELASTIC_PASSWORD and LLM_API_KEY
    ```
3.  **Dependencies**: 
    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
4.  **Run**: 
    ```bash
    python server.py
    ```
    You should see "Connected to Elastic" in the logs.
