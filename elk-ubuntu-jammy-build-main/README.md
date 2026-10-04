# ELK Ubuntu Jammy Build

Production-ready, single-host ELK Stack installation for Ubuntu 22.04 (Jammy) with agentless architecture. Elasticsearch runs on localhost with TLS, while Kibana and Logstash are LAN-accessible. Includes automated certificate generation, idempotent configuration, and comprehensive log ingestion pipelines for Windows (WEF), Syslog, and Kaspersky.

---

## Features

- **One-command installation**: `elk_setup_ubuntu_jammy.sh`
- **Network architecture**:
  - Elasticsearch: `https://localhost:9200` (localhost only, TLS enabled)
  - Kibana: `http://0.0.0.0:5601` (LAN accessible)
  - Logstash inputs:
    - Beats (FortiGate, etc.) → 5044/tcp
    - WEF/Winlogbeat (WEC → Logstash) → 5045/tcp
    - Syslog RFC3164 → 5514/tcp, 5514/udp
    - Syslog RFC5424 → 5515/tcp
    - Kaspersky → 5516/tcp, 5516/udp
- **Certificates**: CA + HTTP (PKCS#12) + Transport (PEM) — SAN: `localhost`, `127.0.0.1`, `::1`
- **Idempotent**: Clean GPG/repo setup, `vm.max_map_count`, systemd drop-in, keystore, roles/users
- **ECS-aligned normalization** with data streams + ILM (90-day retention)

---

## Architecture

```
[Windows Clients] --WEF/GPO--> [WEC] --Winlogbeat(→5045/tcp)--> [Logstash] --> [Elasticsearch (localhost/TLS)]
[Linux/Network/Kaspersky] --Syslog(5514/5515/5516)--> [Logstash] --> [Elasticsearch]
User <-- 5601 HTTP --> Kibana --(Enrollment Token + elastic)--> Elasticsearch (localhost)
```

**Note**: This is an "agentless" deployment; no agents are installed on clients, only Winlogbeat on the WEC server.

---

## Directory Structure

```
elk-ubuntu-jammy-build/
├── scripts/
│   └── install/
│       ├── elk_setup_ubuntu_jammy.sh    # Main installation script
│       └── setup_logstash_ingest.sh     # Logstash pipeline setup
├── config/
│   ├── elasticsearch/
│   │   └── elasticsearch.yml            # Elasticsearch configuration
│   ├── kibana/
│   │   └── kibana.yml                   # Kibana configuration
│   ├── logstash/
│   │   ├── conf.d/                      # Pipeline configurations
│   │   │   ├── fortigate.conf
│   │   │   ├── windows_wef.conf
│   │   │   ├── syslog.conf
│   │   │   └── kaspersky.conf
│   │   └── pipelines.yml
│   └── detection-rules/
│       └── siem.rules.yml               # SIEM detection rules
├── client-configs/
│   └── windows/
│       └── gpo/                         # Group Policy configurations
│           ├── winlogbeat/              # Winlogbeat deployment
│           ├── sysmon/                  # Sysmon deployment
│           ├── heartbeat/               # Heartbeat monitoring
│           └── metricbeat/              # Metricbeat monitoring
├── docs/
│   ├── components/
│   │   ├── elasticsearch.md             # Elasticsearch documentation
│   │   ├── logstash.md                  # Logstash documentation
│   │   └── kibana.md                    # Kibana documentation
│   ├── installation-guide.md            # Detailed installation guide
│   ├── troubleshooting.md               # Troubleshooting guide
│   └── overview.md                      # Project overview
├── website/
│   ├── index.html                       # Educational website landing page
│   ├── pages/                           # Additional website pages
│   ├── css/                             # Stylesheets
│   ├── js/                              # JavaScript files
│   └── assets/                          # Images and resources
├── archive/                             # Historical materials
│   └── old-pdfs/                        # Legacy documentation
└── README.md
```


---

## Requirements

- **OS**: Ubuntu 22.04 LTS (Jammy)
- **Privileges**: root/sudo
- **Network**: Internet access (Elastic APT repository)
- **Recommended resources** (~20 GB/day): 8 vCPU / 32 GB RAM / NVMe SSD (≥1 TB, depends on retention policy)

---

## Quick Start

```bash
git clone https://github.com/yusufarbc/ELK-Ubuntu-Jammy-Build.git
cd ELK-Ubuntu-Jammy-Build
chmod +x scripts/install/elk_setup_ubuntu_jammy.sh
sudo ./scripts/install/elk_setup_ubuntu_jammy.sh
```

**Script output includes**:
- Kibana URL: `http://<Server_IP_or_FQDN>:5601`
- Elastic username/password
- Kibana enrollment token
- Logstash credentials (user: `logstash_ingest`, password in keystore as `ES_PW`)

---

## Post-Installation

### Service Status

```bash
systemctl status elasticsearch kibana logstash --no-pager
```

### Elasticsearch Health (TLS + CA)

```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200 | jq .
```

### Logstash Pipeline Validation

```bash
sudo /usr/share/logstash/bin/logstash --path.settings /etc/logstash -t
```

### Kibana First Login

- Browser: `http://<Server_IP_or_FQDN>:5601`
- Enrollment token: (from script output)
- Username: `elastic` (password from script output)

---

## Connecting Log Sources

### Windows (WEF/WEC + single Winlogbeat)

1. **WEC (Collector) preparation** (Windows Server):

```powershell
wecutil qc
winrm quickconfig
```

2. **GPO**: Configure clients with Subscription Manager (source-initiated), pointing to WEC address.

3. **Winlogbeat** (on WEC only) → `ForwardedEvents` → Logstash 5045/tcp

```yaml
winlogbeat.event_logs:
  - name: ForwardedEvents
output.logstash:
  hosts: ["<logstash_host>:5045"]
```

### Linux & Network Devices (Syslog)

- **Target**: 5514/udp (or 5514/tcp), RFC5424: 5515/tcp
- **rsyslog example**:

```conf
# /etc/rsyslog.d/90-logstash.conf
*.*  @<logstash_host>:5514   # UDP
#*.* @@<logstash_host>:5514  # TCP
```

```bash
sudo systemctl restart rsyslog
```

### Kaspersky

- If KSC/Agent can send syslog, target: 5516/udp,tcp
- If JSON available, send to same port (pipeline parses JSON)

---

## ILM and Data Streams

- **Data stream name**: `logs-<dataset>-default` (e.g., `logs-windows-default`, `logs-fortigate-default`)
- **ILM policy**: `logs-90d` (90-day deletion)
- **Index template**: `logs-default` (pattern: `logs-*-*`, `fortigate-logs-*`; 1 shard / 0 replica / ILM=logs-90d)

**Control commands**:

```bash
# Data stream list
curl -s --cacert /etc/elasticsearch/certs/ca.crt -u elastic:<PW> https://localhost:9200/_data_stream?pretty
# ILM policy
curl -s --cacert /etc/elasticsearch/certs/ca.crt -u elastic:<PW> https://localhost:9200/_ilm/policy/logs-90d?pretty
# Index template
curl -s --cacert /etc/elasticsearch/certs/ca.crt -u elastic:<PW> https://localhost:9200/_index_template/logs-default?pretty
```

---

## Reinstallation / Cleanup

```bash
sudo systemctl stop logstash kibana elasticsearch || true
sudo rm -rf /etc/elasticsearch /etc/kibana /etc/logstash
sudo rm -rf /etc/systemd/system/elasticsearch.service.d
sudo rm -rf /var/log/elasticsearch /var/log/logstash
sudo rm -rf /var/lib/elasticsearch /var/lib/logstash
sudo rm -f /etc/default/logstash /etc/sysconfig/logstash
sudo systemctl daemon-reload
# Then re-run:
# cd ELK-Ubuntu-Jammy-Build && sudo ./scripts/install/elk_setup_ubuntu_jammy.sh
```

---

## Documentation

The documentation is organized into several categories to support both deployment and deep technical understanding.

### Deployment & Operations
- [Installation Guide](docs/installation-guide.md): Detailed step-by-step setup instructions.
- [Troubleshooting Guide](docs/troubleshooting.md): Solutions for common errors (services, network, certificates).
- [Project Overview](docs/overview.md): High-level architectural summary and goals.

### Component Guides
Configuration details and operational basics for each stack component:
- [Elasticsearch Component Guide](docs/elasticsearch.md)
- [Logstash Component Guide](docs/logstash.md)
- [Kibana Component Guide](docs/kibana.md)

### Technical Deep Dives (Architecture & Internals)
Detailed monographs on the internal mechanics of the Elastic Stack:
- [History and Evolution](docs/history-and-evolution.md): From Compass to the ELK Trinity and licensing changes.
- [Elasticsearch Internals](docs/elasticsearch-internals.md): Lucene segments, replication, BKD trees, and Zen2 consensus.
- [Ingestion Architecture](docs/ingestion-architecture.md): Logstash Persistent Queues and Beats/Lumberjack protocols.
- [Kibana Internals](docs/kibana-internals.md): Plugin architecture, Saved Objects, and multi-tenancy.
- [Security Architecture](docs/security-architecture.md): ECS, Elastic Endpoint, "Reflex" engine, and EQL.
- [Comparative Analysis](docs/comparative-analysis.md): Data structures and protocol breakdown.

### Educational Resources
- [Interactive Website](website/index.html): Local educational website structure (open `website/index.html` in browser).

---

## License

- Targets **Elastic Stack Basic** (free tier)
- Elasticsearch is localhost-only; Kibana and Logstash are LAN-accessible (firewall/security groups required)
- Scripts provided "as is"; review against your organizational policies before production use

**Feedback / Issues**: Welcome and appreciated.

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description

---

## Support

For issues and questions:
- Open an issue on GitHub
- Check the [troubleshooting guide](docs/troubleshooting.md)
- Review the [installation guide](docs/installation-guide.md)
