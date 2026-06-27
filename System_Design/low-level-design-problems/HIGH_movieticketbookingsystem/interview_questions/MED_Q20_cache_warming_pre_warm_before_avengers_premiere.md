# Q20: Cache Warming - Pre-warm before Avengers premiere

```java
@Component
public class CacheWarmingService {
    
    @Scheduled(cron = "0 0 9 * * *")  // 9 AM daily
    public void warmCacheBeforeTicketSales() {
        
        log.info("Starting cache warming...");
        
        // Find popular movies (releasing today or tomorrow)
        List<Movie> popularMovies = movieRepository
            .findByReleaseDateBetween(
                LocalDate.now(),
                LocalDate.now().plusDays(1)
            );
        
        for (Movie movie : popularMovies) {
            
            // Warm movie details
            cacheService.set(
                "movie:" + movie.getId(),
                movie,
                Duration.ofHours(24)
            );
            
            // Find all shows
            List<Show> shows = showRepository
                .findByMovieIdAndDateAfter(
                    movie.getId(),
                    LocalDate.now()
                );
            
            for (Show show : shows) {
                // Warm show details
                cacheService.set(
                    "show:" + show.getId(),
                    show,
                    Duration.ofHours(6)
                );
                
                // Warm seat map (all AVAILABLE initially)
                List<Seat> seats = seatRepository
                    .findByScreenId(show.getScreenId());
                
                Map<Long, SeatStatus> seatMap = seats.stream()
                    .collect(Collectors.toMap(
                        Seat::getId,
                        seat -> SeatStatus.AVAILABLE
                    ));
                
                cacheService.set(
                    "show:" + show.getId() + ":seats",
                    seatMap,
                    Duration.ofMinutes(30)
                );
                
                // Warm theater details
                Theater theater = theaterRepository
                    .findById(show.getTheaterId())
                    .orElseThrow();
                
                cacheService.set(
                    "theater:" + theater.getId(),
                    theater,
                    Duration.ofHours(24)
                );
            }
        }
        
        log.info("Cache warming completed for {} movies", 
                 popularMovies.size());
    }
}
```

---

## Key Takeaways:

```
Q11-Q15: Search Optimization
✅ Elasticsearch for full-text + geo
✅ Pagination limits results
✅ Cache with 5-min TTL
✅ Faceted search via aggregations
✅ Autocomplete with completion suggester

Q16-Q20: Caching Strategies
✅ Invalidate + Pub/Sub for real-time
✅ Lock-based refresh prevents stampede
✅ Cache-aside pattern for seat data
✅ Redis for Pub/Sub + data structures
✅ Pre-warm cache before peak load
```

This demonstrates production caching expertise! 🎯
