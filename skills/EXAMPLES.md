# Example Scenarios

This document provides detailed walkthroughs of common observability analysis scenarios.

## Scenario 1: High Saturation, Metrics Within Spec

**Input Data:**
```
Service: api-gateway
Environment: production (us-east-1)
Time Range: Last 30 minutes
Recent Changes: None

Metrics:
- CPU: 75% (baseline: 55%)
- Memory: 68% (baseline: 52%)
- p50 latency: 45ms
- p95 latency: 145ms (SLO: <200ms)
- p99 latency: 180ms
- Error rate: 0.05% (SLO: <0.1%)
- Request rate: 2,450 req/s (typical: 2,200 req/s)
```

**Expected Analysis:**

```
**Status**: Healthy

**Key Findings:**

Note - Resource utilization elevated but within capacity
- CPU: 75% (up 20% from 55% baseline)
- Memory: 68% (up 16% from 52% baseline)
- Latency: p95 145ms, p99 180ms (well below 200ms SLO)
- Errors: 0.05% (well below 0.1% SLO)
- Request rate: 2,450 req/s (11% above baseline, within expected variance)
Confidence: High

**No action recommended right now.** Resource saturation is higher than baseline but all user-facing metrics (latency, errors) remain well within SLO targets. The elevated saturation correlates with slightly higher request rate, which is within normal traffic patterns. No negative trends detected.

**Watch Items:**
- Monitor for continued upward trend in CPU/memory over next 2 hours
- Set alert if CPU exceeds 85% sustained for >10 minutes
- Review capacity planning for next traffic growth phase
- Consider horizontal scaling during next maintenance window if trend continues
```

---

## Scenario 2: Saturation High + Latency Trending Up

**Input Data:**
```
Service: checkout-service
Environment: production (eu-west-1)
Time Range: Last 45 minutes
Recent Changes: None in last 24 hours

Metrics (15 minutes ago):
- CPU: 82%
- p95 latency: 185ms
- Error rate: 0.06%

Metrics (current):
- CPU: 88% (sustained)
- p95 latency: 220ms (trending up ~5ms/min)
- p99 latency: 340ms
- Error rate: 0.08%
- Request rate: 1,850 req/s (stable)
- Database connection pool: 78/100 (was 60/100)
```

**Expected Analysis:**

```
**Status**: Degraded

**Key Findings:**

SEV2 - MEDIUM
**Component**: checkout-service (eu-west-1)
**Metric**: p95 latency breached SLO: 220ms (target: <200ms), increasing ~5ms/min
**Evidence**: 
- Started degrading 15 minutes ago
- CPU saturation: 88% sustained (up from 82%)
- Error rate stable but elevated: 0.08%
- Database connection pool utilization increased: 78/100 (was 60/100)
- Request rate stable at 1,850 req/s - not traffic-driven
**Confidence**: High
**Duration**: 15 minutes and worsening

**Recommended Actions:**

DO NOW:
1. Scale horizontally: add 2 instances to current pool of 6 (expect 5-7 min deployment, should reduce CPU to ~60%)
2. Monitor p95 latency for return to <180ms after scale operation completes
3. If latency doesn't improve within 10 min post-scale, proceed to NEXT steps

NEXT:
4. Review top endpoints by latency in APM - identify if specific endpoint causing issue
5. Check for database query performance issues:
   - Query execution times in database logs
   - Check for lock contention or slow queries
   - Review connection pool settings
6. Examine GC metrics for memory pressure or long GC pauses
7. Check for thread pool exhaustion or blocking operations
8. Analyze recent code changes in last 7 days for potential N+1 queries

**Watch Items:**
- **ESCALATE to SEV1** if latency exceeds 300ms OR errors rise above 0.2%
- Monitor error rate closely - often lags latency degradation by 5-10 minutes
- Database connection pool at 78% - if reaches 90%, will cause connection timeouts

**Data to Confirm:**
1. Top 5 slowest endpoints in APM for last 20 minutes
2. Database slow query log entries >500ms
3. Thread dump showing thread states and potential blocking
```

---

## Scenario 3: Error Spike After Deployment

**Input Data:**
```
Service: payment-processor
Environment: production (all regions)
Time Range: Last 25 minutes
Recent Changes: v3.2.0 deployed at 10:12 UTC

Metrics:
- 10:10 UTC (pre-deploy): Error rate 0.1%, p95 latency 145ms
- 10:15 UTC (3 min post-deploy): Error rate 2.5%, p95 latency 150ms
- 10:35 UTC (current): Error rate 2.4%, p95 latency 155ms

Error Breakdown:
- 90% NullPointerException in PaymentProcessor.validate()
- 10% HTTP 500 from downstream payment gateway

Affected Requests: ~450 users/min experiencing failures
Request Rate: 18,000 req/min (unchanged from baseline)
```

**Expected Analysis:**

```
**Status**: Incident

**Key Findings:**

SEV1 - HIGH
**Component**: payment-processor (all regions)
**Metric**: Error rate: 2.4% (24x baseline of 0.1%), far exceeds 0.5% SLO
**Evidence**:
- Spike onset: 10:15 UTC, exactly 3 minutes after v3.2.0 deploy completed (10:12 UTC)
- Top error: "NullPointerException in PaymentProcessor.validate()" (90% of errors)
- Error rate remains elevated (2.4%) after 23 minutes - not recovering
- Latency stable: p95 155ms, not contributing to errors
- 450 users/min unable to complete payments
**Confidence**: High (clear temporal correlation with deploy, specific error signature)
**Duration**: 23 minutes

**Recommended Actions:**

DO NOW (within 5 minutes):
1. **ROLLBACK** payment-processor to v3.1.9 (last known good) - expect 7 min recovery window
   - Rollback command: `kubectl rollout undo deployment/payment-processor -n production`
   - Alternative: If rollback faster, toggle feature flag `enable_new_validation` to false
2. Notify #incidents channel: "SEV1: Payment processing failing at 2.4% due to v3.2.0, rolling back"
3. Page on-call SRE and Payment team lead
4. Monitor error rate - expect drop to <0.2% within 10 minutes of rollback completion

NEXT (post-mitigation, within 2 hours):
5. Root cause analysis:
   - Review all changes to `PaymentProcessor.validate()` in v3.2.0 commit
   - Examine failed request traces in APM/Datadog for null input sources
   - Check if null validation was removed or if new code path introduced
   - Identify which payment methods/regions affected (if not all)
6. Add defensive null-check unit tests before attempting re-deploy
7. Implement canary deployment strategy for payment-processor (5% → 25% → 100%)
8. Add monitoring alert: error rate >0.5% for >5 minutes should page immediately

**Watch Items:**
- Confirm error rate drops below 0.2% within 10 min of rollback
- Monitor payment gateway errors separately (10% of current errors)
- Check for duplicate payment submissions if users retried failed transactions

**Data to Confirm:**
1. Error rate response to rollback: target <0.2% within 10 minutes
2. v3.1.9 git diff for PaymentProcessor.validate() - identify what changed
3. Sample failed request payloads showing null values
```

---

## Scenario 4: Cascading Failure Detection

**Input Data:**
```
Service: user-service → auth-service → database
Environment: production (us-west-2)
Time Range: Last 20 minutes

user-service metrics:
- p95 latency: 450ms (was 120ms) 
- Error rate: 0.8% (was 0.05%)
- Timeout errors: 85% of errors

auth-service metrics:
- p95 latency: 3.2s (was 180ms)
- Error rate: 0.3% (was 0.02%)
- Database connection errors: 70% of errors

database metrics:
- CPU: 95%
- Active connections: 485/500 (max pool size)
- Query execution time: p95 2.8s (was 250ms)
- Slow query: getUserPermissions() appearing in 60% of slow queries
```

**Expected Analysis:**

```
**Status**: Incident

**Key Findings:**

SEV1 - HIGH (Cascading Failure)
**Root Cause Component**: Database (us-west-2)
**Cascading Impact**: user-service ← auth-service ← database

**Primary Issue**:
**Component**: Database
**Metric**: CPU at 95%, connection pool exhausted (485/500), query latency p95 2.8s (was 250ms)
**Evidence**: Slow query identified - `getUserPermissions()` in 60% of slow queries
**Confidence**: High
**Duration**: 20 minutes

**Secondary Impact**:
- auth-service: p95 latency 3.2s (16x baseline), 0.3% errors (database connection timeouts)
- user-service: p95 latency 450ms (3.75x baseline), 0.8% errors (auth-service timeouts)

**Failure Chain**:
1. Database query `getUserPermissions()` performance degraded (root cause)
2. Database connection pool exhausted (485/500 connections)
3. auth-service waiting for database connections → latency spike → timeouts
4. user-service calling auth-service → experiencing timeouts → elevated errors

**Recommended Actions:**

DO NOW (within 10 minutes):
1. **Database optimization**:
   - Kill long-running queries: Identify and terminate `getUserPermissions()` queries >5s
   - Add index if missing on permissions table (user_id, resource_id)
   - Scale database read replicas (add 2 replicas) if query is read-heavy
2. **Temporary relief**:
   - Increase auth-service connection pool timeout from 5s to 15s
   - Enable auth-service circuit breaker to fail fast instead of queuing
   - Scale auth-service horizontally (+3 instances) to handle increased latency
3. **Monitoring**:
   - Watch for database CPU to drop below 80%
   - Confirm auth-service latency drops to <500ms
   - Verify user-service errors return to <0.1%

NEXT (within 2 hours):
4. **Root cause analysis**:
   - Analyze `getUserPermissions()` query execution plan
   - Check if recent permission data growth caused index inefficiency
   - Review if query can be optimized or cached
   - Investigate what triggered the query pattern change
5. **Preventive measures**:
   - Implement query result caching in Redis (TTL: 5 min)
   - Add database query timeout limits (max 2s)
   - Set up connection pool monitoring alerts (>85% utilization)
   - Configure progressive timeout strategies between services

**Watch Items:**
- Database connection pool must drop below 400/500 to confirm recovery
- Monitor for query time improvement after index added
- Check for downstream services also calling auth-service

**Data to Confirm:**
1. getUserPermissions() query execution plan and table statistics
2. Recent permission table growth (rows added in last 7 days)
3. auth-service call patterns (request rate to database vs baseline)
```

---

## Scenario 5: False Positive Identification

**Input Data:**
```
Service: analytics-aggregator (batch job)
Environment: production
Time Range: 02:00-04:00 UTC daily
Alert: "High Memory Usage - 92% for 30+ minutes"

Metrics:
- Memory: 92% (triggers at 90%)
- CPU: 35%
- Error rate: 0%
- Job completion time: 1h 45min (typical: 1h 40min)
- Historical pattern: Memory spikes to 90-95% daily during 02:00-04:00 UTC window

Context:
- This is a scheduled batch job processing previous day's analytics data
- Runs daily at 02:00 UTC
- Memory usage returns to 40% after job completes at ~04:00 UTC
- No user-facing impact (batch processing only)
```

**Expected Analysis:**

```
**Status**: Healthy (False Positive Alert)

**Key Findings:**

Note - Expected batch processing behavior
**Component**: analytics-aggregator (batch job)
**Metric**: Memory 92% during scheduled batch window (02:00-04:00 UTC)
**Evidence**:
- This is a known daily pattern occurring during batch processing window
- Memory spikes to 90-95% consistently during 02:00-04:00 UTC every day
- Returns to 40% baseline after job completion
- Job completion time: 1h 45min (5 min longer than typical 1h 40min, within variance)
- Zero errors, CPU at healthy 35%
- No user-facing impact (internal batch processing)
**Confidence**: High
**Duration**: 2 hours (expected duration)

**No action recommended right now.** This memory spike is expected behavior for the daily analytics batch job. The alert threshold (90%) is too sensitive for this workload's normal operating pattern. The job is completing successfully with no errors or user impact.

**Recommended Actions:**

NEXT (non-urgent, next maintenance window):
1. **Tune alert threshold**:
   - Suppress memory alerts for analytics-aggregator during 01:45-04:15 UTC window
   - Or increase threshold to 95% specifically for this service
   - Or create separate alert: "Memory >95% for >30 min OUTSIDE batch window"
2. **Consider optimization** (if growth trend continues):
   - Review if job can be paginated/chunked to reduce memory footprint
   - Evaluate if memory limit can be increased for this specific job
   - Check for memory leaks if completion time trend increasing >10% month-over-month

**Watch Items:**
- Monitor job completion time trend - currently 1h 45min vs 1h 40min baseline (3% variance, acceptable)
- Alert if job fails to complete or takes >2h 30min (50% longer than baseline)
- Track memory spike pattern - if starts occurring outside 02:00-04:00 window, investigate

**Data to Confirm:**
1. Historical completion times for last 30 days - confirm 1h 40min ± 10min is normal
2. Memory usage pattern same time yesterday and 7 days ago
3. Data volume processed (rows/GB) vs historical to confirm workload not growing unexpectedly
```

---

## Key Takeaways

**Pattern Recognition:**
1. Correlate metrics across multiple signals (latency + saturation, errors + deployments)
2. Consider temporal context (batch jobs, deployment windows, traffic patterns)
3. Identify cascading failures by tracing dependencies
4. Distinguish expected behavior from true anomalies

**Action Prioritization:**
1. User impact drives severity classification
2. Include rollback plans for every recommended action
3. Separate immediate actions from follow-up investigations
4. Provide specific metrics to confirm recovery

**Communication:**
1. Always include actual values with units
2. State confidence levels in findings
3. Explain why something is or isn't an issue
4. Reference time ranges and durations explicitly
