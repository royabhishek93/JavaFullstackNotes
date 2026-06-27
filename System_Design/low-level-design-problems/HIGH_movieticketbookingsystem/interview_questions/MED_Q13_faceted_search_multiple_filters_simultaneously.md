# Q13: Faceted Search - Multiple filters simultaneously

```java
// User selects: Genre=Action, Language=Hindi, Rating>4, Distance<5km

public SearchResponse facetedSearch(FacetedQuery query) {
    
    BoolQueryBuilder boolQuery = QueryBuilders.boolQuery();
    
    // Genre filter
    if (query.getGenres() != null) {
        boolQuery.must(QueryBuilders.termsQuery("genre", query.getGenres()));
    }
    
    // Language filter
    if (query.getLanguages() != null) {
        boolQuery.must(QueryBuilders.termsQuery("language", query.getLanguages()));
    }
    
    // Rating filter
    if (query.getMinRating() != null) {
        boolQuery.must(QueryBuilders.rangeQuery("rating")
            .gte(query.getMinRating()));
    }
    
    // Geo-spatial filter (theaters within 5km)
    if (query.getUserLocation() != null) {
        boolQuery.must(QueryBuilders.geoDistanceQuery("theater_location")
            .point(query.getUserLocation().getLat(), 
                   query.getUserLocation().getLon())
            .distance("5km"));
    }
    
    // Build aggregations for facet counts
    NativeSearchQuery esQuery = NativeSearchQueryBuilder()
        .withQuery(boolQuery)
        .addAggregation(AggregationBuilders.terms("by_genre").field("genre"))
        .addAggregation(AggregationBuilders.terms("by_language").field("language"))
        .addAggregation(AggregationBuilders.terms("by_rating").field("rating"))
        .build();
    
    return elasticsearchTemplate.search(esQuery, MovieDocument.class);
}
```

---
