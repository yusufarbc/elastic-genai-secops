[← Back to README](../README.md)

# Troubleshooting Guide

## General Troubleshooting Steps

1. **Check service status**:
```bash
sudo systemctl status elasticsearch kibana logstash
```

2. **View logs**:
```bash
sudo journalctl -u elasticsearch -n 100 --no-pager
sudo journalctl -u kibana -n 100 --no-pager
sudo journalctl -u logstash -n 100 --no-pager
```

3. **Verify network connectivity**:
```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200
curl -s http://localhost:5601/api/status
```

---

## Elasticsearch

### Service Won't Start

**Symptoms**: `systemctl status elasticsearch` shows failed state

**Common Causes**:

1. **Insufficient memory**
   ```bash
   # Check available memory
   free -h
   # Reduce heap size in /etc/elasticsearch/jvm.options
   -Xms2g
   -Xmx2g
   ```

2. **vm.max_map_count too low**
   ```bash
   # Check current value
   sysctl vm.max_map_count
   # Set to required value
   sudo sysctl -w vm.max_map_count=262144
   ```

3. **Permission issues**
   ```bash
   sudo chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
   sudo chown -R elasticsearch:elasticsearch /var/log/elasticsearch
   ```

4. **Port already in use**
   ```bash
   sudo netstat -tlnp | grep 9200
   # Kill process or change port in elasticsearch.yml
   ```

### Certificate Errors

**Symptoms**: SSL/TLS handshake failures

**Solutions**:

1. **Verify certificates exist**:
   ```bash
   ls -la /etc/elasticsearch/certs/
   ```

2. **Check certificate permissions**:
   ```bash
   sudo chmod 0644 /etc/elasticsearch/certs/ca.crt
   sudo chmod 0640 /etc/elasticsearch/certs/*.key
   sudo chown root:elasticsearch /etc/elasticsearch/certs/*
   ```

3. **Regenerate certificates**:
   ```bash
   sudo rm -rf /etc/elasticsearch/certs/*
   # Re-run installation script or certificate generation section
   ```

### Out of Memory Errors

**Symptoms**: `OutOfMemoryError` in logs

**Solutions**:

1. **Increase heap size** (up to 50% of RAM):
   ```bash
   sudo nano /etc/elasticsearch/jvm.options
   # Set -Xms and -Xmx to same value
   -Xms4g
   -Xmx4g
   sudo systemctl restart elasticsearch
   ```

2. **Reduce shard count**:
   ```bash
   # Update index template to use fewer shards
   curl -X PUT "https://localhost:9200/_index_template/logs-default" \
     --cacert /etc/elasticsearch/certs/ca.crt \
     -u elastic:<password> \
     -H 'Content-Type: application/json' \
     -d '{"template":{"settings":{"number_of_shards":1}}}'
   ```

### Cluster Health Yellow/Red

**Symptoms**: Cluster health not green

**Solutions**:

1. **Check unassigned shards**:
   ```bash
   curl -s --cacert /etc/elasticsearch/certs/ca.crt \
     -u elastic:<password> \
     "https://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"
   ```

2. **For single-node setup, set replicas to 0**:
   ```bash
   curl -X PUT "https://localhost:9200/_settings" \
     --cacert /etc/elasticsearch/certs/ca.crt \
     -u elastic:<password> \
     -H 'Content-Type: application/json' \
     -d '{"index":{"number_of_replicas":0}}'
   ```

---

## Kibana

### Cannot Connect to Elasticsearch

**Symptoms**: Kibana shows "Kibana server is not ready yet"

**Solutions**:

1. **Verify Elasticsearch is running**:
   ```bash
   curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200
   ```

2. **Check Kibana configuration**:
   ```bash
   sudo nano /etc/kibana/kibana.yml
   # Verify:
   elasticsearch.hosts: ["https://localhost:9200"]
   elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca.crt"]
   ```

3. **Verify CA certificate**:
   ```bash
   ls -la /etc/kibana/certs/ca.crt
   sudo cp /etc/elasticsearch/certs/ca.crt /etc/kibana/certs/
   sudo systemctl restart kibana
   ```

### Enrollment Token Issues

**Symptoms**: Enrollment fails or token expired

**Solutions**:

1. **Generate new token**:
   ```bash
   sudo /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -s kibana
   ```

2. **Verify http.p12 exists**:
   ```bash
   ls -la /etc/elasticsearch/certs/http.p12
   ```

3. **Manual enrollment**:
   ```bash
   sudo /usr/share/kibana/bin/kibana-setup --enrollment-token <new_token>
   sudo systemctl restart kibana
   ```

### Encryption Key Errors

**Symptoms**: "Saved object encryption key is missing" error

**Solutions**:

1. **Generate encryption keys**:
   ```bash
   sudo /usr/share/kibana/bin/kibana-encryption-keys generate -q --force
   ```

2. **Update environment file**:
   ```bash
   sudo nano /etc/kibana/kibana.env
   # Add generated keys:
   KBN_SECURITY_KEY=<key>
   KBN_SAVEDOBJ_KEY=<key>
   KBN_REPORTING_KEY=<key>
   ```

3. **Restart Kibana**:
   ```bash
   sudo systemctl restart kibana
   ```

### Port 5601 Not Accessible

**Symptoms**: Cannot access Kibana from browser

**Solutions**:

1. **Check firewall**:
   ```bash
   sudo ufw status
   sudo ufw allow 5601/tcp
   ```

2. **Verify binding**:
   ```bash
   sudo netstat -tlnp | grep 5601
   # Should show 0.0.0.0:5601
   ```

3. **Check server.host in kibana.yml**:
   ```yaml
   server.host: "0.0.0.0"
   ```

---

## Logstash

### Pipeline Won't Start

**Symptoms**: Logstash service fails or pipeline errors

**Solutions**:

1. **Test configuration**:
   ```bash
   sudo /usr/share/logstash/bin/logstash \
     --path.settings /etc/logstash -t
   ```

2. **Check syntax errors**:
   ```bash
   sudo journalctl -u logstash -n 200 --no-pager | grep -i error
   ```

3. **Verify configuration files**:
   ```bash
   ls -la /etc/logstash/conf.d/
   # Ensure .conf files are present and readable
   ```

### Cannot Connect to Elasticsearch

**Symptoms**: "Connection refused" or authentication errors

**Solutions**:

1. **Verify keystore password**:
   ```bash
   sudo /usr/share/logstash/bin/logstash-keystore \
     --path.settings /etc/logstash list
   ```

2. **Check ES_PW in keystore**:
   ```bash
   # Re-add password
   echo "<password>" | sudo /usr/share/logstash/bin/logstash-keystore \
     --path.settings /etc/logstash add --force ES_PW
   ```

3. **Verify CA certificate**:
   ```bash
   ls -la /etc/logstash/certs/ca.crt
   sudo cp /etc/elasticsearch/certs/ca.crt /etc/logstash/certs/
   ```

4. **Test Elasticsearch connection**:
   ```bash
   curl -s --cacert /etc/logstash/certs/ca.crt \
     -u logstash_ingest:<password> \
     https://localhost:9200
   ```

### No Data Ingestion

**Symptoms**: Logs not appearing in Elasticsearch

**Solutions**:

1. **Check input ports**:
   ```bash
   sudo netstat -tlnp | grep -E '5044|5045|5514|5515|5516'
   ```

2. **Test log sending**:
   ```bash
   # Test syslog
   echo "test message" | nc localhost 5514
   
   # Check Logstash logs
   sudo tail -f /var/log/logstash/logstash-plain.log
   ```

3. **Verify pipeline stats**:
   ```bash
   curl -s http://localhost:9600/_node/stats/pipelines?pretty
   ```

4. **Check firewall**:
   ```bash
   sudo ufw allow 5044/tcp
   sudo ufw allow 5045/tcp
   sudo ufw allow 5514/tcp
   sudo ufw allow 5514/udp
   sudo ufw allow 5515/tcp
   sudo ufw allow 5516/tcp
   sudo ufw allow 5516/udp
   ```

### Grok Parse Failures

**Symptoms**: `_grokparsefailure` tag in logs

**Solutions**:

1. **Test grok patterns**:
   - Use Kibana Dev Tools Grok Debugger
   - Or use online grok debugger

2. **Add debug output**:
   ```ruby
   output {
     stdout { codec => rubydebug }
   }
   ```

3. **Check sample logs**:
   ```bash
   sudo tail -f /var/log/logstash/logstash-plain.log | grep grok
   ```

---

## Network and Connectivity

### Firewall Configuration

**Ubuntu UFW**:
```bash
# Kibana
sudo ufw allow 5601/tcp

# Logstash inputs
sudo ufw allow 5044/tcp  # Beats
sudo ufw allow 5045/tcp  # WEF
sudo ufw allow 5514/tcp  # Syslog TCP
sudo ufw allow 5514/udp  # Syslog UDP
sudo ufw allow 5515/tcp  # RFC5424
sudo ufw allow 5516/tcp  # Kaspersky TCP
sudo ufw allow 5516/udp  # Kaspersky UDP

# Enable firewall
sudo ufw enable
sudo ufw status
```

### DNS Resolution

If using hostnames instead of IPs:

```bash
# Test DNS resolution
nslookup <hostname>
ping <hostname>

# Add to /etc/hosts if needed
echo "192.168.1.100 elk-server" | sudo tee -a /etc/hosts
```

---

## Performance Issues

### High CPU Usage

**Solutions**:

1. **Reduce Logstash workers**:
   ```yaml
   # /etc/logstash/logstash.yml
   pipeline.workers: 2
   ```

2. **Optimize Elasticsearch queries**:
   - Use filters in Kibana
   - Limit time ranges
   - Use index patterns

3. **Monitor resource usage**:
   ```bash
   top
   htop
   iostat -x 1
   ```

### High Disk Usage

**Solutions**:

1. **Check index sizes**:
   ```bash
   curl -s --cacert /etc/elasticsearch/certs/ca.crt \
     -u elastic:<password> \
     "https://localhost:9200/_cat/indices?v&s=store.size:desc"
   ```

2. **Adjust ILM policy**:
   - Reduce retention from 90 days
   - Enable index rollover

3. **Delete old indices**:
   ```bash
   curl -X DELETE "https://localhost:9200/logs-old-*" \
     --cacert /etc/elasticsearch/certs/ca.crt \
     -u elastic:<password>
   ```

---

## Getting Help

If issues persist:

1. **Check official documentation**:
   - [Elasticsearch Docs](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
   - [Logstash Docs](https://www.elastic.co/guide/en/logstash/current/index.html)
   - [Kibana Docs](https://www.elastic.co/guide/en/kibana/current/index.html)

2. **Community forums**:
   - [Elastic Discuss](https://discuss.elastic.co/)
   - [Stack Overflow](https://stackoverflow.com/questions/tagged/elk)

3. **GitHub Issues**:
   - Open an issue in this repository with:
     - Error messages
     - Log excerpts
     - Configuration files (sanitized)
     - Steps to reproduce
