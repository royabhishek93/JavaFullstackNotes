# Q11: Search Optimization - "Avengers in Mumbai" returning 10M results in <200ms

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Elasticsearch + Cache + Pagination

```java
@Service
public class SearchOptimizationService {
    
    @Cacheable(value = "search", key = "#query.getCacheKey()")
    public SearchResponse searchMovies(SearchQuery query) {
        
        // Build Elasticsearch query
        NativeSearchQuery esQuery = NativeSearchQueryBuilder()
            .withQuery(QueryBuilders.boolQuery()
                .must(QueryBuilders.multiMatchQuery(
                    query.getTitle(),
                    "title^3", "synopsis", "cast"  // Title boost 3x
                ))
                .filter(QueryBuilders.termQuery("city", query.getCity()))
                .filter(QueryBuilders.rangeQuery("show_date")
                    .gte(query.getDate()))
            )
            .withPageable(PageRequest.of(0, 20))  // Only 20 results
            .build();
        
        // Execute search (50-100ms typical)
        SearchHits<MovieDocument> hits = elasticsearchTemplate
            .search(esQuery, MovieDocument.class);
        
        return SearchResponse.from(hits);
    }
}
```

**Optimization Techniques:**
```
1. Pagination: Return 20 results, not 10M
2. Cache: 5-min TTL (acceptable staleness)
3. Index optimization: Pre-computed fields
4. Query filtering: City + date narrows results
5. Field boosting: title^3 (relevance ranking)
```

---
