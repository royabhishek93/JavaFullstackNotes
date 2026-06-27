# Q14: Autocomplete - Search suggestions with 100k concurrent users

```java
@Service
public class AutocompleteService {
    
    // Use Redis sorted set for fast prefix matching
    public List<String> getSuggestions(String prefix, int limit) {
        
        String cacheKey = "autocomplete:" + prefix.toLowerCase();
        
        // Check cache first (sub-10ms)
        List<String> cached = redisTemplate
            .opsForList()
            .range(cacheKey, 0, limit - 1);
        
        if (cached != null && !cached.isEmpty()) {
            return cached;
        }
        
        // Cache miss: Query Elasticsearch
        CompletionSuggestionBuilder suggestionBuilder = 
            SuggestBuilders.completionSuggestion("title.suggest")
                .prefix(prefix)
                .size(limit);
        
        SuggestBuilder suggestBuilder = new SuggestBuilder()
            .addSuggestion("movie-suggest", suggestionBuilder);
        
        SearchRequest searchRequest = new SearchRequest("movies")
            .source(SearchSourceBuilder()
                .suggest(suggestBuilder));
        
        SearchResponse response = elasticsearchClient.search(searchRequest);
        
        List<String> suggestions = response.getSuggest()
            .getSuggestion("movie-suggest")
            .getEntries()
            .get(0)
            .getOptions()
            .stream()
            .map(option -> option.getText().string())
            .collect(Collectors.toList());
        
        // Cache for 1 hour
        redisTemplate.opsForList().rightPushAll(cacheKey, suggestions);
        redisTemplate.expire(cacheKey, Duration.ofHours(1));
        
        return suggestions;
    }
}
```

**Elasticsearch Index Mapping:**
```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "fields": {
          "suggest": {
            "type": "completion"
          }
        }
      }
    }
  }
}
```

---
