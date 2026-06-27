# HIGH Q01 - Scale Video Delivery to Global Users

## Scenario
Need to serve millions of concurrent viewers across regions.

## Design
- Store video segments in object storage.
- Use CDN edge caches globally.
- Keep manifests cacheable but authorization-aware when needed.
- Separate metadata API scaling from media delivery scaling.
- Pre-warm popular content in CDN.

## Bottlenecks
- Cache miss storms on new viral video
- Origin egress cost
- Region-level skew for hot content

## Interview One-Liner
At global scale, CDN architecture matters more than application server count.
