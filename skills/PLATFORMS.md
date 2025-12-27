# Platform-Specific Guidance

This document provides detailed guidance for analyzing metrics from specific observability platforms.

## Prometheus

### Key Characteristics
- Pull-based metrics collection
- Time-series database with PromQL query language
- Label-based data model
- Typically used with Grafana for visualization

### Metric Naming Conventions
- `http_requests_total` - Counter of all HTTP requests
- `http_request_duration_seconds` - Histogram of request durations
- `process_cpu_seconds_total` - CPU usage counter
- `process_resident_memory_bytes` - Memory usage gauge

### Analysis Tips
- **Use label filtering** to narrow scope: `http_requests_total{service="api",status="500"}`
- **Rate calculations** for counters: `rate(http_requests_total[5m])`
- **Percentile calculations** from histograms: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **Aggregations** across instances: `sum by (service) (rate(http_requests_total[5m]))`

### Common Issues
- **Missing data gaps**: Check Prometheus scrape failures, target down
- **High cardinality labels**: Can cause performance issues, look for labels with many unique values
- **Stale metrics**: Check `up` metric to verify target health
- **Counter resets**: Identified by sudden drops in counter values, usually from restarts

### Example Queries
```promql
# Error rate percentage
100 * sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# p95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Saturation - CPU usage
100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

---

## Datadog

### Key Characteristics
- Agent-based metrics collection
- APM (Application Performance Monitoring) with distributed tracing
- Integrated logs, metrics, and traces
- Rich tagging system

### Metric Types
- **Gauges**: Point-in-time values (memory usage, queue length)
- **Counts**: Number of events in interval
- **Rates**: Events per second
- **Histograms**: Statistical distribution (p50, p95, p99, avg, max)

### Analysis Tips
- **Correlate with traces**: When latency spikes, drill into trace flamegraphs
- **Use tags effectively**: Filter by `env:prod`, `service:api`, `version:v2.1.0`
- **APM Service Map**: Visualize dependencies to identify cascading failures
- **Error Tracking**: Automatic grouping of similar errors with stack traces

### Platform-Specific Features
- **Anomaly Detection**: ML-based detection of unusual patterns
- **Watchdog**: Automatically surfaces potential issues
- **Deployment Tracking**: Correlate metrics with deploy events
- **Synthetic Monitoring**: Proactive checks from external locations

### Common Patterns
- **Latency analysis**: Check both application latency AND infrastructure metrics
- **Error correlation**: Link errors to specific traces showing full request path
- **Resource attribution**: Tag metrics with team, cost-center for attribution
- **SLO tracking**: Built-in SLO monitoring with error budget burn rate

### Investigation Flow
1. Start with service-level metrics (RED: Rate, Errors, Duration)
2. If degraded, examine APM traces for slow operations
3. Correlate with infrastructure metrics (CPU, memory, disk, network)
4. Check deployment tracking for recent changes
5. Review error tracking for error patterns and affected endpoints

---

## New Relic

### Key Characteristics
- Full-stack observability platform
- NRQL (New Relic Query Language) similar to SQL
- Transaction tracing with detailed breakdowns
- Infrastructure, APM, Browser, Mobile monitoring

### Metric Organization
- **Application metrics**: Response time, throughput, error rate
- **Transaction traces**: Detailed breakdown of slow transactions
- **Database queries**: Time spent in database operations
- **External services**: Third-party API calls and latency

### Analysis Tips
- **Transaction breakdown**: Identify which component (app, database, external) contributes most to latency
- **Key transactions**: Focus on business-critical endpoints first
- **Apdex score**: Quick health indicator (Satisfied/Tolerating/Frustrated users)
- **Error rate vs response time**: Separate user experience (latency) from reliability (errors)

### NRQL Examples
```sql
-- Error rate over time
SELECT percentage(count(*), WHERE error IS true) 
FROM Transaction 
FACET appName 
TIMESERIES 5 minutes

-- p95 latency by endpoint
SELECT percentile(duration, 95) 
FROM Transaction 
WHERE appName = 'api-gateway' 
FACET name 
SINCE 1 hour ago

-- Database query time distribution
SELECT average(databaseDuration), max(databaseDuration) 
FROM Transaction 
WHERE appName = 'checkout-service' 
TIMESERIES AUTO
```

### Investigation Flow
1. Check overview dashboard: Apdex, response time, throughput, error rate
2. Drill into slow transactions (>2x baseline)
3. Examine transaction traces to identify bottleneck layer
4. Review database queries if database time is significant
5. Check external service calls for third-party API issues
6. Correlate with infrastructure metrics (CPU, memory, disk IO)

---

## CloudWatch

### Key Characteristics
- AWS-native monitoring service
- Metrics delayed by ~1-5 minutes
- Namespace-based organization (AWS/EC2, AWS/RDS, AWS/Lambda, custom)
- Dimensions for filtering (InstanceId, FunctionName, etc.)

### Important Considerations
- **Metric delay**: CloudWatch metrics can lag 1-5 minutes, especially custom metrics
- **Aggregation periods**: Metrics aggregated at 1-min, 5-min, or longer intervals
- **Detailed monitoring**: 1-minute granularity requires enabling (extra cost)
- **Regional**: Metrics are region-specific

### Key Metrics by Service

**EC2/ECS:**
- `CPUUtilization`: Percentage CPU usage
- `NetworkIn/Out`: Bytes transferred
- `StatusCheckFailed`: Instance health

**RDS:**
- `DatabaseConnections`: Active connections
- `CPUUtilization`: Database CPU
- `ReadLatency/WriteLatency`: Disk I/O latency
- `FreeableMemory`: Available memory

**Lambda:**
- `Invocations`: Function execution count
- `Duration`: Execution time
- `Errors`: Function failures
- `Throttles`: Rate-limited invocations
- `ConcurrentExecutions`: Parallel executions

**ALB/ELB:**
- `TargetResponseTime`: Backend latency
- `HTTPCode_Target_5XX_Count`: Backend errors
- `RequestCount`: Total requests
- `HealthyHostCount/UnhealthyHostCount`: Target health

### Analysis Tips
- **Account for delay**: When investigating recent issues, metrics may not be complete yet
- **Use GetMetricStatistics API**: For programmatic analysis with Statistics: Average, Sum, Maximum, Minimum, SampleCount
- **Percentiles**: Only available for custom metrics with detailed statistics
- **Alarm evaluation**: Understand evaluation periods and datapoints to alarm

### Common Patterns
- **Lambda cold starts**: High Duration + low Invocations = cold start latency
- **RDS connection exhaustion**: DatabaseConnections approaching max_connections
- **ECS/EC2 memory pressure**: Check CloudWatch Agent for MemoryUtilization
- **ALB 5xx vs 4xx**: 5xx = backend issues, 4xx = client errors

### Investigation Flow
1. Check service-specific dashboards (EC2, RDS, Lambda, ALB)
2. Correlate multiple metrics across services (ALB latency + RDS CPU)
3. Review CloudWatch Logs Insights for application logs
4. Check AWS Health Dashboard for service issues
5. Verify metric completeness given aggregation delay

---

## Grafana

### Key Characteristics
- Visualization and dashboard platform (not a metrics backend)
- Supports multiple data sources (Prometheus, InfluxDB, CloudWatch, etc.)
- Dashboard templating with variables
- Alert rule definitions and notifications

### Analysis Tips
- **Dashboard context**: Understand which data source powers each panel
- **Variable usage**: Check dashboard variables for filtering (environment, region, service)
- **Alert annotations**: Look for alert firing markers on graphs
- **Panel queries**: Examine panel edit mode to see underlying queries
- **Time range**: Verify time range matches the period you're investigating

### Common Dashboard Patterns
- **RED dashboards**: Rate, Errors, Duration for services
- **USE dashboards**: Utilization, Saturation, Errors for resources
- **Comparison dashboards**: Multiple services or environments side-by-side

### Investigation Flow
1. Use service-specific dashboards for overview
2. Drill into problematic time ranges using time picker
3. Check alert history panel for correlation with issues
4. Examine individual panel queries if data looks suspicious
5. Cross-reference with source system (Prometheus, CloudWatch) if needed

---

## Elastic Stack (ELK)

### Key Characteristics
- Log aggregation and analysis platform
- Elasticsearch for storage and search
- Kibana for visualization
- Structured and unstructured log support

### Log Analysis Tips
- **Structured logging**: JSON logs are easier to query and aggregate
- **Field extraction**: Use Logstash/Filebeat processors to extract fields
- **Aggregations**: Count, average, percentiles, terms (top N)
- **Filters**: Combine multiple conditions with AND/OR/NOT

### Common Queries (Kibana Query Language)
```
# Find errors in last 15 minutes
level:"ERROR" AND timestamp:[now-15m TO now]

# Top error messages
level:"ERROR" | stats count() by message

# Slow requests (>1s)
response_time > 1000 AND path.keyword:"/api/checkout"

# Error rate percentage
(level:"ERROR" OR level:"WARN") | stats count() / total_count()
```

### Investigation Flow
1. Start with error-level logs in the problematic time range
2. Group by error message or exception type to identify patterns
3. Drill into specific log entries for stack traces and context
4. Check for request IDs to trace through distributed systems
5. Correlate log volume spikes with application metrics
6. Review slow query logs if database-related

### Best Practices
- **Use request IDs**: Trace requests across services
- **Log sampling**: In high-traffic systems, sample non-error logs
- **Retention policies**: Balance storage costs with retention needs
- **Index patterns**: Separate indices by service or date for performance

---

## Cross-Platform Analysis

When working with metrics from multiple platforms:

### Unified Approach
1. **Normalize metric names**: Different platforms use different naming (latency vs duration vs response_time)
2. **Align time ranges**: Account for clock skew and metric delays between systems
3. **Correlate by timestamp**: Use absolute timestamps, not relative "5 minutes ago"
4. **Trace IDs**: Use distributed tracing headers (X-Request-ID, X-Trace-ID) to correlate across platforms

### Priority Order
1. Start with user-facing metrics (latency, errors from ALB/LB)
2. Drill into application metrics (APM, traces)
3. Check infrastructure metrics (CPU, memory, disk, network)
4. Review platform metrics (RDS, Lambda, container orchestration)
5. Examine logs for detailed context

### Handling Metric Discrepancies
- **Different aggregation windows**: One platform shows 1-min avg, another shows 5-min avg
- **Clock skew**: Timestamps may differ by seconds between systems
- **Sampling differences**: Some tools sample, others collect all data points
- **Precision**: CloudWatch often has lower resolution than Prometheus

When metrics disagree:
1. Verify time ranges are identical
2. Check aggregation methods (avg vs p95)
3. Consider sampling rates
4. Prefer lower-level/raw data sources
5. Document which source is considered canonical for your organization
