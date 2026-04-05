# Q61: Multi-Region Architecture - Deploy BookMyShow globally

**Difficulty:** ⭐⭐⭐⭐⭐ (Principal)

```
SINGLE REGION (Current)
═══════════════════════════════════════════════════════════
All users → US-East-1
- India users: 200-300ms latency ❌
- Europe users: 150-200ms latency ❌
- Single point of failure ❌


MULTI-REGION (Target)
═══════════════════════════════════════════════════════════
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  US-East-1  │  │  EU-West-1  │  │ AP-South-1  │
│  (Primary)  │  │  (Secondary)│  │ (Secondary) │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
    Americas        Europe            Asia
    50ms           40ms              30ms


ROUTING: GeoDNS (Route 53)
═══════════════════════════════════════════════════════════
User in India → AP-South-1 (30ms) ✅
User in UK → EU-West-1 (40ms) ✅
User in USA → US-East-1 (50ms) ✅
```

**Deployment Strategy:**

```yaml
# terraform/multi-region.tf

# US-East-1 (Primary)
module "us_east_1" {
  source = "./modules/region"
  region = "us-east-1"
  is_primary = true
  
  services = {
    booking_service = { instances = 100 }
    payment_service = { instances = 50 }
    user_service = { instances = 30 }
  }
  
  database = {
    instance_class = "db.r5.4xlarge"
    read_replicas = 5
  }
}

# EU-West-1 (Secondary)
module "eu_west_1" {
  source = "./modules/region"
  region = "eu-west-1"
  is_primary = false
  
  services = {
    booking_service = { instances = 50 }
    payment_service = { instances = 25 }
    user_service = { instances = 15 }
  }
  
  database = {
    instance_class = "db.r5.2xlarge"
    read_replicas = 3
  }
}

# AP-South-1 (Secondary)
module "ap_south_1" {
  source = "./modules/region"
  region = "ap-south-1"
  is_primary = false
  
  services = {
    booking_service = { instances = 80 }  # Higher: India traffic
    payment_service = { instances = 40 }
    user_service = { instances = 25 }
  }
  
  database = {
    instance_class = "db.r5.4xlarge"
    read_replicas = 4
  }
}
```

---
