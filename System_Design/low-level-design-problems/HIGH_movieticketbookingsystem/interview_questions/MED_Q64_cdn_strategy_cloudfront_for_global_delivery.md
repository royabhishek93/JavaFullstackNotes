# Q64: CDN Strategy - CloudFront for global delivery

**Difficulty:** ⭐⭐⭐ (Senior)

```java
@Configuration
public class CDNConfig {
    
    // Static assets → CloudFront
    @Bean
    public String cdnBaseUrl() {
        return "https://d123abc.cloudfront.net";
    }
    
    // Cache-Control headers
    @GetMapping("/api/movies/{id}/poster")
    public ResponseEntity<byte[]> getMoviePoster(@PathVariable Long id) {
        
        byte[] poster = movieService.getPoster(id);
        
        return ResponseEntity.ok()
            .cacheControl(CacheControl
                .maxAge(7, TimeUnit.DAYS)
                .cachePublic())
            .header("CDN-Cache-Control", "max-age=2592000")  // 30 days
            .body(poster);
    }
}
```

**CloudFront Distribution:**

```yaml
# Static Assets
Origin: s3://bookmyshow-assets
Path: /assets/*
Cache Behavior:
  - Min TTL: 1 day
  - Max TTL: 365 days
  - Default TTL: 7 days
  - Compress: true

# API (Dynamic Content)
Origin: api.bookmyshow.com
Path: /api/*
Cache Behavior:
  - Min TTL: 0
  - Max TTL: 1 hour
  - Default TTL: 5 minutes
  - Forward Headers: Authorization, X-User-Id
```

---
