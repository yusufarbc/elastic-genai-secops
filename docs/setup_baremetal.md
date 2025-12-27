[← Back to README](../README.md)

# Ubuntu 22.04 Single-Server Agentless SIEM Installation and Operations Guide

## Introduction

This guide explains the installation and operation of an agentless Elastic SIEM stack (no Elastic Agent/Fleet) running on a single Ubuntu 22.04 server. Elasticsearch listens only on localhost with TLS; Kibana and Logstash are LAN-accessible. The goal is to provide a secure, idempotent installation with a single command.

## Components and Architecture

- **Elasticsearch** (localhost:9200, TLS)
- **Kibana** (0.0.0.0:5601, HTTP)
- **Logstash** (Beats 5044/tcp, WEF 5045/tcp, Syslog 5514/udp+tcp, 5515/tcp, Kaspersky 5516/udp+tcp)

```
[Clients] -> [Logstash] -> [Elasticsearch]
User <-> Kibana <-> Elasticsearch
```

## Installation

```bash
git clone https://github.com/yusufarbc/ELK-Ubuntu-Jammy-Build.git
cd ELK-Ubuntu-Jammy-Build
chmod +x scripts/install/elk_setup_ubuntu_jammy.sh
sudo ./scripts/install/elk_setup_ubuntu_jammy.sh
```

The script output displays: Elastic password, Kibana enrollment token, and Logstash keystore information (ES_PW).

## Verification

```bash
systemctl status elasticsearch kibana logstash --no-pager
curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200 | jq .
sudo /usr/share/logstash/bin/logstash --path.settings /etc/logstash -t
```

## Log Sources

- **Windows WEF**: Winlogbeat (WEC) → Logstash 5045/tcp
- **Syslog**: 5514/udp(+tcp), RFC5424: 5515/tcp
- **Kaspersky**: 5516/udp,tcp (JSON supported)

## Data Streams and ILM

- **Data stream**: `logs-<dataset>-default`
- **ILM**: `logs-90d` (90-day retention)

## Troubleshooting

- **Kibana won't connect**: Check ES health, verify Kibana `elasticsearch.hosts` configuration
- **Enrollment token generation**: Run `elasticsearch-create-enrollment-token -s kibana`
- **Logstash not writing**: Check `journalctl -u logstash -f`, verify `ES_PW` in keystore

## Cleanup

```bash
sudo systemctl stop logstash kibana elasticsearch || true
sudo rm -rf /etc/elasticsearch /etc/kibana /etc/logstash
sudo rm -rf /etc/systemd/system/elasticsearch.service.d
sudo rm -rf /var/log/elasticsearch /var/log/logstash
sudo rm -rf /var/lib/elasticsearch /var/lib/logstash
sudo rm -f /etc/default/logstash /etc/sysconfig/logstash
sudo systemctl daemon-reload
```

## Notes

- Kibana remains HTTP on LAN; reverse proxy/SSL not required for lab environments
- This guide is maintained in English for international accessibility
