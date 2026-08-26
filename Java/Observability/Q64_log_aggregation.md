# 🎯 Q64: Log Aggregation (ELK Stack, Splunk)?

> **Interview Frequency:** 35% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

App has 100 instances. Each logs to local file. Can't find error across all!

---

## 📌 ELK Stack

**Elasticsearch** (Index logs)  
**Logstash** (Parse & forward)  
**Kibana** (Visualize & query)

---

## 📌 Setup

```yaml
# Logback XML sends to Logstash
<appender name="logstash" class="net.logstash.logback.appender.LogstashTcpSocketAppender">
    <destination>logstash:5000</destination>
    <encoder class="net.logstash.logback.encoder.LogstashEncoder" />
</appender>

# Logstash receives, parses, sends to Elasticsearch
input {
  tcp {
    port => 5000
    codec => json
  }
}

output {
  elasticsearch {
    hosts => "elasticsearch:9200"
  }
}

# Kibana queries Elasticsearch
GET kibana/discover
# Search: service.name="payment" AND level="ERROR"
```

---

## ✅ Benefits

1. **Centralized** - All logs in one place
2. **Searchable** - Query across all instances
3. **Alerting** - Alert on error patterns
4. **Visualization** - Dashboards for monitoring

---

## 💬 Interview Tip (Say This Exactly)

"Use ELK (Elasticsearch, Logstash, Kibana) or Splunk for log aggregation. Send JSON logs for easy parsing. Search errors across all 100 instances. Set alerts for error spikes."

---

**Last Updated:** February 22, 2026  
**All 64 Questions Complete! ✅**
