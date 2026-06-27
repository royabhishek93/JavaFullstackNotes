# Q15: Geo-spatial Search - Find theaters within 5km, sorted by distance

```java
public List<Theater> findNearbyTheaters(
        double userLat, 
        double userLon, 
        double radiusKm) {
    
    NativeSearchQuery query = NativeSearchQueryBuilder()
        .withQuery(QueryBuilders.geoDistanceQuery("location")
            .point(userLat, userLon)
            .distance(radiusKm + "km"))
        .withSort(SortBuilders.geoDistanceSort("location", userLat, userLon)
            .order(SortOrder.ASC)
            .unit(DistanceUnit.KILOMETERS))
        .withPageable(PageRequest.of(0, 20))
        .build();
    
    SearchHits<Theater> hits = elasticsearchTemplate
        .search(query, Theater.class);
    
    return hits.stream()
        .map(hit -> {
            Theater theater = hit.getContent();
            // Calculate and set distance
            double distance = hit.getSortValues().get(0);
            theater.setDistance(distance);
            return theater;
        })
        .collect(Collectors.toList());
}
```

---
