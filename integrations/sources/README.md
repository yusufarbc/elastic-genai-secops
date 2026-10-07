# Log source integrations

One folder per source. Each folder holds the Logstash pipeline and, where needed, the collector
configuration for the sending side. `pipelines.yml` enables all of them; remove a block to disable a source.

## Ports and data streams

| Source | Folder | Listens on | Sender | Data stream |
| --- | --- | --- | --- | --- |
| Palo Alto (Filebeat) | `paloalto/logstash-beats.conf` | 5044/tcp (beats) | Filebeat `panw` module | `logs-paloalto-*` |
| Windows | `windows/logstash.conf` | 5045/tcp (beats) | Winlogbeat on endpoints or on a WEC server | `logs-windows-*` |
| Metricbeat / Heartbeat | `beats-health/logstash.conf` | 5046/tcp (beats) | Metricbeat, Heartbeat | `metrics-metricbeat-*`, `logs-heartbeat-*` |
| Kaspersky | `kaspersky/logstash.conf` | 5047/tcp (beats) | Filebeat reading the KSC syslog export | `logs-kaspersky-*` |
| Syslog | `syslog/logstash.conf` | 5514/udp+tcp (RFC3164), 5515/tcp (RFC5424) | Any syslog sender | `logs-syslog-*` |
| FortiGate | `fortigate/logstash.conf` | 5516/udp+tcp | FortiGate syslog (key=value) | `logs-fortigate-*` |
| Palo Alto (syslog) | `paloalto/logstash-syslog.conf` | 5517/udp+tcp | PAN-OS syslog server profile | `logs-paloalto-*` |

All ports are above 1024 so Logstash can run unprivileged. The namespace (`*`) is `default` unless
`ES_NAMESPACE` is set.

## Pipeline settings

Every pipeline reads its Elasticsearch connection from environment variables, so the same files work
on bare metal and in containers:

| Variable | Default | Set by |
| --- | --- | --- |
| `ES_HOSTS` | `https://localhost:9200` | compose / `/etc/default/logstash` |
| `ES_USER` | `logstash_ingest` | |
| `ES_PW` | (required) | Logstash keystore (bare metal) or environment (compose) |
| `ES_CA_CERT` | `/etc/logstash/certs/ca.crt` | |
| `ES_NAMESPACE` | `default` | |
| `LS_SOURCES_DIR` | `/etc/logstash/conf.d` | location of this folder on the Logstash host |
| `FORTIGATE_TZ`, `PANOS_TZ` | `UTC` | time zone of the device clocks |

The `logstash_ingest` user and its `logstash_writer` role are created by `content/bootstrap.sh`.

## Windows: load the Winlogbeat ingest pipelines

Winlogbeat 8 parses Security, Sysmon and PowerShell events in Elasticsearch ingest pipelines. When
Winlogbeat ships through Logstash, those pipelines must be loaded once per Winlogbeat version, from any
Windows host that can reach Elasticsearch:

```powershell
.\winlogbeat.exe setup --pipelines `
  -E output.logstash.enabled=false `
  -E 'output.elasticsearch.hosts=["https://ELK_SERVER:9200"]' `
  -E output.elasticsearch.username=elastic -E output.elasticsearch.password=<password> `
  -E 'output.elasticsearch.ssl.certificate_authorities=["C:\path\to\ca.crt"]'
```

On the bare-metal install Elasticsearch listens on localhost only; use an SSH tunnel
(`ssh -L 9200:localhost:9200 <elk-host>`) and `https://localhost:9200`.
Without these pipelines events are stored, but fields such as `process.name` and `event.category`
are missing and the Windows detection rules cannot match.

Sysmon configuration: [`windows/sysmon/sysmon.xml`](windows/sysmon/sysmon.xml).

## Palo Alto: two options

- **Syslog direct** (simplest): point a PAN-OS syslog server profile at port 5517. TRAFFIC and THREAT
  logs are parsed into ECS fields; other log types are stored raw.
- **Filebeat panw module** (complete parsing): PAN-OS sends to rsyslog on a collector host
  (`paloalto/collector/rsyslog-30-paloalto.conf`, UDP 5518), Filebeat reads the file and ships it to 5044.
  Load the module's ingest pipeline once with `filebeat setup --pipelines --modules panw`.

## Test a pipeline

Send a syslog line and look for it in Kibana (Discover, data view `logs-*`):

```bash
logger -n <logstash-host> -P 5514 -d "esm test message"
```
