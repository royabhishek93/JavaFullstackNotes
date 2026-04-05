# Q33: Load Balancer Configuration - Health checks, sticky sessions

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: AWS ALB Configuration

**Application Load Balancer (Layer 7):**

```yaml
# AWS ALB Terraform configuration
resource "aws_lb" "main" {
  name               = "bookmyshow-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection = true
  enable_http2              = true
  
  tags = {
    Environment = "production"
  }
}

resource "aws_lb_target_group" "app" {
  name     = "app-servers"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/actuator/health"
    matcher             = "200"
  }
  
  deregistration_delay = 30  # Drain connections for 30s
  
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 3600  # 1 hour
    enabled         = true
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.main.arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

**Health Check Endpoint:**

```java
@RestController
@RequestMapping("/actuator")
public class HealthCheckController {
    
    private final DataSource dataSource;
    private final RedisTemplate redisTemplate;
    
    @GetMapping("/health")
    public ResponseEntity<HealthResponse> health() {
        
        HealthResponse response = new HealthResponse();
        response.setStatus("UP");
        response.setTimestamp(LocalDateTime.now());
        
        // Check database
        try {
            dataSource.getConnection().close();
            response.setDatabase("UP");
        } catch (Exception e) {
            response.setDatabase("DOWN");
            response.setStatus("DOWN");
        }
        
        // Check Redis
        try {
            redisTemplate.opsForValue().get("health:check");
            response.setCache("UP");
        } catch (Exception e) {
            response.setCache("DOWN");
            response.setStatus("DOWN");
        }
        
        // Check disk space
        File root = new File("/");
        long usableSpace = root.getUsableSpace();
        long totalSpace = root.getTotalSpace();
        double usagePercent = 
            ((double) (totalSpace - usableSpace) / totalSpace) * 100;
        
        if (usagePercent > 90) {
            response.setDisk("WARN");
            response.setStatus("WARN");
        } else {
            response.setDisk("UP");
        }
        
        int statusCode = response.getStatus().equals("UP") ? 200 : 503;
        return ResponseEntity.status(statusCode).body(response);
    }
}

@Data
class HealthResponse {
    private String status;
    private String database;
    private String cache;
    private String disk;
    private LocalDateTime timestamp;
}
```

**Load Balancing Algorithms:**

```
ROUND ROBIN (Default)
═══════════════════════════════════════════════════════════
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A (cycle repeats)

Pros: Simple, even distribution
Cons: Ignores server load


LEAST CONNECTIONS
═══════════════════════════════════════════════════════════
Server A: 10 connections
Server B: 5 connections  ← Choose this
Server C: 8 connections

Request → Server B (least loaded)

Pros: Better for long-lived connections
Cons: Overhead to track connections


WEIGHTED ROUND ROBIN
═══════════════════════════════════════════════════════════
Server A (c5.4xlarge): Weight 2
Server B (c5.2xlarge): Weight 1
Server C (c5.2xlarge): Weight 1

Request 1 → Server A
Request 2 → Server A
Request 3 → Server B
Request 4 → Server C
Request 5 → Server A (cycle repeats)

Pros: Utilize heterogeneous servers
Cons: Complex configuration
```

---
