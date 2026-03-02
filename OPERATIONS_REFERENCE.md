# Q-Shield Monitoring & Operations Reference Guide

## Metrics Reference

### Application Metrics

#### Request Metrics
```
http_request_duration_seconds_bucket{le="+Inf",...}      # Request latency histogram
http_request_duration_seconds_sum{endpoint="/users",...}  # Total request time
http_request_duration_seconds_count{status="200",...}     # Total requests
http_requests_total{status="200",method="GET",...}        # Total requests by status
```

**Healthy Baseline:**
- P50 latency: 50-100ms
- P95 latency: 200-500ms
- P99 latency: 500-1000ms
- Success rate: >99.9%
- Error rate: <0.1%

#### Database Metrics
```
db_connection_pool_size{pool="default"}                   # Connection pool size
db_connection_pool_checked_out{pool="default"}            # Active connections
db_query_duration_seconds{query="SELECT...",...}          # Query latency
db_slow_queries_total{query="...",...}                    # Slow queries (>1s)
db_transaction_rollback_total                             # Rolled back transactions
```

**Healthy Baseline:**
- Average query time: 10-50ms
- Connection pool utilization: 30-60%
- Slow queries: <5/min
- Deadlocks: 0-2/day

#### Cache Metrics
```
redis_connected_clients                                   # Connected clients
redis_used_memory_bytes                                   # Memory used
redis_commands_processed_total{command="GET",...}         # Commands executed
redis_hits_total / redis_misses_total                     # Cache effectiveness
redis_evicted_keys_total                                  # Keys evicted
```

**Healthy Baseline:**
- Hit rate: 70-95%
- Commands/sec: 1000-5000
- Memory usage: 50-80% of allocated
- Evictions: <100/min

#### System Metrics
```
container_cpu_usage_seconds_total                         # Container CPU usage
container_memory_usage_bytes                              # Container memory
disk_usage_bytes{mountpoint="/var/lib/postgresql"}        # Disk usage
network_receive_bytes_total / network_transmit_bytes_total # Network I/O
```

**Healthy Baseline:**
- CPU: 20-40% average
- Memory: 40-60% of allocated
- Disk: <70% utilized
- Network: <50% capacity

## Alert Rules

### Critical Alerts (Page On-Call)
```promql
# Service down
up{job="qshield-api"} == 0

# High error rate (>1% for 5 min)
(rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) > 0.01

# Database unreachable
pg_up == 0

# Disk almost full (>85%)
(node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15

# Out of memory
container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9

# High latency (P95 >2000ms)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2

# Redis unreachable
redis_up == 0

# Pod crash loop (restart >5 times in 5 min)
rate(kube_pod_container_status_restarts_total[5m]) > 5
```

### Warning Alerts (Alert via Slack)
```promql
# Moderate error rate (>0.5% for 10 min)
(rate(http_requests_total{status=~"5.."}[10m]) / rate(http_requests_total[10m])) > 0.005

# Slow responses (P95 >1000ms for 10 min)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[10m])) > 1

# Cache hit rate low (<60% for 15 min)
(rate(redis_hits_total[15m]) / (rate(redis_hits_total[15m]) + rate(redis_misses_total[15m]))) < 0.6

# CPU high (>70% for 10 min)
rate(container_cpu_usage_seconds_total[1m]) > 0.7

# Memory high (>80% for 10 min)
(container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.8

# Disk usage increasing (projected to fill in 7 days)
predict_linear(node_filesystem_avail_bytes[1h], 7*24*3600) < 0
```

## Log Search Patterns

### Elasticsearch Queries

#### API Errors
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "service": "qshield-api" } },
        { "range": { "timestamp": { "gte": "now-1h" } } },
        { "match": { "level": "ERROR" } }
      ]
    }
  },
  "aggs": {
    "errors_by_endpoint": {
      "terms": { "field": "endpoint.keyword", "size": 10 }
    },
    "errors_over_time": {
      "date_histogram": { "field": "timestamp", "interval": "5m" }
    }
  }
}
```

#### Slow Database Queries
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "log_type": "DATABASE" } },
        { "range": { "query_duration_ms": { "gte": 1000 } } },
        { "range": { "timestamp": { "gte": "now-1d" } } }
      ]
    }
  },
  "sort": [{ "query_duration_ms": { "order": "desc" } }],
  "size": 20
}
```

#### Failed Authentication
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "endpoint": "/auth/*" } },
        { "range": { "status_code": { "gte": 400, "lt": 500 } } },
        { "range": { "timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "aggs": {
    "failures_by_user": {
      "terms": { "field": "user_id.keyword", "size": 20 }
    },
    "failures_by_ip": {
      "terms": { "field": "client_ip.keyword", "size": 20 }
    }
  }
}
```

#### Task Queue Issues
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "component": "TASK_QUEUE" } },
        { "range": { "timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "tasks_by_status": {
      "terms": { "field": "status.keyword" }
    },
    "processing_time": {
      "stats": { "field": "duration_ms" }
    }
  }
}
```

## Dashboard Queries

### Grafana Panels

#### Request Rate & Success
```promql
# Request rate (req/sec)
rate(http_requests_total[5m])

# Success rate (%)
(rate(http_requests_total{status=~"2..|3.."}[5m]) / rate(http_requests_total[5m])) * 100

# Error rate (%)
(rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) * 100
```

#### API Latency
```promql
# P50
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# P99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

#### Database Health
```promql
# Active connections
db_connection_pool_checked_out

# Connection pool size
db_connection_pool_size

# Query duration (average)
rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])

# Slow queries per minute
rate(db_slow_queries_total[1m])
```

#### Cache Performance
```promql
# Cache hit rate
(rate(redis_hits_total[5m]) / (rate(redis_hits_total[5m]) + rate(redis_misses_total[5m]))) * 100

# Memory usage
redis_used_memory_bytes / 1024 / 1024 {format: short, unit: MB}

# Commands/sec
rate(redis_commands_processed_total[1m])
```

## Runbooks

### Service Health Check

**When:** Service is down or unresponsive

**Steps:**
```bash
# 1. Verify service status
kubectl get pods -n qshield -l app=qshield-api
kubectl describe pod <pod-name> -n qshield

# 2. Check logs
kubectl logs <pod-name> -n qshield --tail=100

# 3. Check resource constraints
kubectl top pod <pod-name> -n qshield

# 4. Verify dependencies
kubectl exec <pod-name> -n qshield -- psql -h postgres.qshield.svc.cluster.local -U qshield -d qshield -c "SELECT 1"
kubectl exec <pod-name> -n qshield -- redis-cli -h redis.qshield.svc.cluster.local ping

# 5. Restart pod if needed
kubectl delete pod <pod-name> -n qshield

# 6. Check auto-scaling
kubectl get hpa -n qshield
```

### High Error Rate

**When:** Error rate exceeds 1% for >5 minutes

**Steps:**
```bash
# 1. Identify error patterns
kubectl logs -n qshield -l app=qshield-api --tail=500 | grep ERROR

# 2. Check error types
# - 5xx errors: Server issues (database, cache, external API, application logic)
# - 4xx errors: Client issues (invalid requests, auth failures)

# 3. For database errors
kubectl exec deployment/qshield-api -n qshield -- psql -h postgres.qshield.svc.cluster.local -U qshield -d qshield \
  -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# 4. For cache errors
kubectl exec deployment/qshield-api -n qshield -- redis-cli -h redis.qshield.svc.cluster.local info stats

# 5. Check for feature flag issues
# Review recent deployments and rollback if necessary
kubectl rollout history deployment/qshield-api -n qshield
kubectl rollout undo deployment/qshield-api -n qshield

# 6. Check external API integration status
# Verify OAuth providers are responding
curl -I https://accounts.google.com
curl -I https://github.com
```

### High Latency

**When:** P95 latency exceeds 2 seconds for >5 minutes

**Steps:**
```bash
# 1. Identify slow endpoints
# Use Kibana or Grafana to find which endpoints are slow

# 2. Check database performance
kubectl exec -it deployment/qshield-api -n qshield -- psql -h postgres.qshield.svc.cluster.local -U qshield -d qshield -c "
  SELECT query, calls, mean_exec_time 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;"

# 3. Check cache efficiency
kubectl exec deployment/qshield-api -n qshield -- redis-cli -h redis.qshield.svc.cluster.local \
  --stat

# 4. Review recent code changes
# Identify if latency started after recent deployment

# 5. Check for N+1 queries
# Review database query logs for repeated queries in single request

# 6. Implement caching
# Add Redis cache for slow queries
# Use batch operations for bulk data

# 7. Optimize database
# Add indexes for frequently searched columns
# Consider query rewrite
```

### Disk Space Alert

**When:** Disk usage exceeds 85%

**Steps:**
```bash
# 1. Check disk usage
kubectl get nodes -o wide
kubectl exec -it <node-name> -- df -h

# 2. Identify large directories
# For database node:
kubectl exec postgres-0 -n qshield -- du -sh /var/lib/postgresql/data/*

# For application node:
kubectl exec <api-pod> -n qshield -- du -sh /app/*

# 3. Clean up logs (if applicable)
kubectl logs --all-containers=true -n qshield --timestamps=true | wc -l

# 4. Check for orphaned resources
docker ps -a | grep exited
docker images | grep none

# 5. For database specifically
# Run VACUUM to reclaim space
kubectl exec postgres-0 -n qshield -- vacuumdb -U qshield -d qshield -v

# 6. Scale up disk or purge old data
# Plan to increase PVC size in next maintenance window
# Delete old logs/backups if safe to do so
```

### Database Connection Issues

**When:** Cannot connect to database

**Steps:**
```bash
# 1. Verify database pod is running
kubectl get pod -n qshield -l app=postgres

# 2. Check database logs
kubectl logs -n qshield postgres-0 --tail=50

# 3. Check network connectivity
kubectl exec -it <api-pod> -n qshield -- nc -zv postgres.qshield.svc.cluster.local 5432

# 4. Verify connection string
kubectl get secret -n qshield qshield-secrets -o jsonpath='{.data.database-password}' | base64 -d

# 5. Test connection
kubectl exec -it postgres-0 -n qshield -- psql -U qshield -d qshield -c "SELECT version();"

# 6. Check connection pool
# View active connections:
kubectl exec -it postgres-0 -n qshield -- psql -U qshield -d qshield -c "
  SELECT count(*) as total_connections 
  FROM pg_stat_activity;"

# 7. Kill idle connections if needed
kubectl exec -it postgres-0 -n qshield -- psql -U qshield -d qshield -c "
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE usename = 'qshield' AND state = 'idle';"
```

### Redis Memory Exhaustion

**When:** Redis memory usage exceeds 90%

**Steps:**
```bash
# 1. Check memory stats
kubectl exec redis-0 -n qshield -- redis-cli -c info memory

# 2. Identify large keys
kubectl exec redis-0 -n qshield -- redis-cli -c \
  --bigkeys

# 3. Check eviction policy
kubectl exec redis-0 -n qshield -- redis-cli -c config get maxmemory-policy

# 4. If policy is acceptable, delete unnecessary keys
kubectl exec redis-0 -n qshield -- redis-cli -c \
  --pattern "*session*" del

# 5. If memory still full, increase Redis memory
# Edit StatefulSet or Helm values
kubectl patch statefulset redis -n qshield -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"2Gi"}}}]}}}}'

# 6. Monitor Redis memory after restart
watch -n 5 'kubectl exec redis-0 -n qshield -- redis-cli info memory'
```

## Escalation Procedures

### Level 1: Alert Processing (On-Call Engineer)
1. Acknowledge alert within 3 minutes
2. Verify alert is genuine (not false positive)
3. Check dashboard for context
4. If critical and unclear, escalate immediately

### Level 2: Investigation
1. Run diagnostics from appropriate runbook
2. Check recent changes/deployments
3. Review logs and metrics
4. Document findings

### Level 3: Escalation
- If unfamiliar with issue
- If issue unresolved after 15 minutes
- If customer impact confirmed

**Escalation Chain:**
1. On-Call Engineer (Primary)
2. Team Lead (Secondary)
3. Director/Manager (Tertiary)
4. VP Engineering (Critical P1)

## SLO/SLA Targets

| Metric | SLO | Alert Threshold |
|--------|-----|-----------------|
| Availability | 99.9% | <99% for 5 min |
| Response Time (P95) | <500ms | >2000ms for 5 min |
| Error Rate | <0.1% | >1% for 5 min |
| Deployment Success | 100% | Any failure |
| MTTR (Mean Time to Restore) | <15 min | Auto-escalation at 10 min |
| MTTD (Mean Time to Detect) | <1 min | Alert configuration |

## On-Call Handoff Template

```
Team: <team-name>
Date: <date>
From: <previous-oncall>
To: <new-oncall>

Active Issues:
- [Issue]: [Status] [ETA]

Recent Changes:
- [Date]: [Change] [Status]

Key Contacts:
- Database expert: <name> <phone>
- Frontend expert: <name> <phone>
- Infrastructure: <name> <phone>

Known Issues:
- [Issue]: [Workaround]

Dashboard: <URL>
Runbooks: <URL>
```

## Useful Commands

```bash
# Get cluster overview
kubectl get nodes,pods,svc -n qshield

# View all events
kubectl get events -n qshield --sort-by='.lastTimestamp'

# Port-forward to service
kubectl port-forward svc/qshield-api 8000:8000 -n qshield

# Execute command in pod
kubectl exec -it <pod> -n qshield -- <command>

# Stream logs
kubectl logs -f <pod> -n qshield

# Describe resource
kubectl describe <resource-type> <resource-name> -n qshield

# Scale deployment
kubectl scale deployment <name> --replicas=<count> -n qshield

# Check resource quotas
kubectl describe quota -n qshield

# View metrics
kubectl top nodes
kubectl top pods -n qshield

# Get access logs
kubectl logs --all-containers=true -l app=qshield-api -n qshield | head -100
```
