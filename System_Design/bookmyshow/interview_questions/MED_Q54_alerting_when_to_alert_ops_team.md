# Q54: Alerting - When to alert ops team?

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Alert on Symptoms, Not Causes

```yaml
# prometheus-alerts.yml

groups:
  - name: booking_alerts
    interval: 30s
    rules:
      
      # Critical: High error rate
      - alert: HighBookingErrorRate
        expr: |
          sum(rate(booking_errors_total[5m]))
          /
          sum(rate(booking_requests_total[5m]))
          > 0.05
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Booking error rate >5%"
          description: "Error rate: {{ $value | humanizePercentage }}"
          runbook: "https://wiki/runbooks/booking-errors"
      
      # Critical: Payment gateway down
      - alert: PaymentGatewayDown
        expr: |
          sum(rate(payment_errors_total{error_type="gateway_timeout"}[5m]))
          > 10
        for: 1m
        labels:
          severity: critical
          team: payments
        annotations:
          summary: "Payment gateway experiencing timeouts"
          description: "{{ $value }} timeouts/sec"
          action: "Check Stripe status page"
      
      # Warning: High latency
      - alert: HighBookingLatency
        expr: |
          histogram_quantile(0.99, 
            rate(booking_duration_bucket[5m])
          ) > 2000
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "P99 booking latency >2s"
          description: "P99: {{ $value }}ms"
      
      # Critical: Database connection pool exhausted
      - alert: DatabasePoolExhausted
        expr: db_connection_pool_utilization > 0.95
        for: 1m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Database connection pool near capacity"
          description: "Utilization: {{ $value | humanizePercentage }}"
          action: "Scale up connection pool or add read replicas"
      
      # Warning: Low cache hit rate
      - alert: LowCacheHitRate
        expr: cache_hit_rate < 0.7
        for: 10m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Cache hit rate <70%"
          description: "Hit rate: {{ $value | humanizePercentage }}"
      
      # Critical: Booking revenue drop
      - alert: RevenueDropDetected
        expr: |
          (
            rate(bookings_revenue_sum[10m])
            <
            rate(bookings_revenue_sum[10m] offset 1h) * 0.5
          )
        for: 5m
        labels:
          severity: critical
          team: business
        annotations:
          summary: "Booking revenue dropped >50%"
          description: "Investigate payment/booking issues"
```

**Alert Routing (AlertManager):**

```yaml
# alertmanager.yml

route:
  receiver: default
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
    # Critical alerts → PagerDuty
    - match:
        severity: critical
      receiver: pagerduty
      continue: true
    
    # Payment alerts → Payment team Slack
    - match:
        team: payments
      receiver: slack-payments
    
    # Business hours only
    - match:
        severity: warning
      receiver: slack-general
      active_time_intervals:
        - business-hours

receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: <pagerduty_key>
        severity: '{{ .GroupLabels.severity }}'
  
  - name: slack-payments
    slack_configs:
      - api_url: <slack_webhook>
        channel: '#alerts-payments'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'
  
  - name: slack-general
    slack_configs:
      - api_url: <slack_webhook>
        channel: '#alerts-general'

time_intervals:
  - name: business-hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '18:00'
```

---
