# Q50: SQL Injection Prevention - Secure database queries

### Difficulty: ⭐⭐ (Mid-Senior)

### ✅ Solution: Parameterized Queries

```java
// ❌ VULNERABLE TO SQL INJECTION
@Repository
public class VulnerableMovieRepository {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    public List<Movie> searchMovies(String title) {
        // NEVER do this!
        String sql = "SELECT * FROM movie WHERE title LIKE '%" + title + "%'";
        return jdbcTemplate.query(sql, new MovieRowMapper());
        
        // Attack example:
        // title = "'; DROP TABLE movie; --"
        // Resulting SQL: SELECT * FROM movie WHERE title LIKE '%'; DROP TABLE movie; --%'
    }
}

// ✅ SAFE - PARAMETERIZED QUERY
@Repository
public class SecureMovieRepository {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    public List<Movie> searchMovies(String title) {
        // Use parameterized query
        String sql = "SELECT * FROM movie WHERE title LIKE ?";
        return jdbcTemplate.query(
            sql,
            new MovieRowMapper(),
            "%" + title + "%"  // Parameter is escaped
        );
    }
}

// ✅ SAFE - JPA NAMED PARAMETERS
@Repository
public interface MovieRepository extends JpaRepository<Movie, Long> {
    
    @Query("SELECT m FROM Movie m WHERE m.title LIKE %:title%")
    List<Movie> searchByTitle(@Param("title") String title);
    
    // Spring Data auto-escapes parameters ✅
}

// ✅ SAFE - CRITERIA API
@Service
public class MovieSearchService {
    
    @Autowired
    private EntityManager entityManager;
    
    public List<Movie> searchMovies(String title, String genre) {
        
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<Movie> query = cb.createQuery(Movie.class);
        Root<Movie> movie = query.from(Movie.class);
        
        List<Predicate> predicates = new ArrayList<>();
        
        if (title != null) {
            predicates.add(cb.like(
                movie.get("title"),
                "%" + title + "%"  // Safe - Criteria API escapes
            ));
        }
        
        if (genre != null) {
            predicates.add(cb.equal(movie.get("genre"), genre));
        }
        
        query.where(predicates.toArray(new Predicate[0]));
        
        return entityManager.createQuery(query).getResultList();
    }
}
```

**Input Validation:**

```java
@RestController
@RequestMapping("/api/movies")
public class MovieController {
    
    @GetMapping("/search")
    public List<Movie> searchMovies(
            @RequestParam @Pattern(regexp = "^[a-zA-Z0-9\\s]+$") String title) {
        
        // Validate input (alphanumeric + spaces only)
        // Blocks SQL injection attempts
        
        return movieRepository.searchByTitle(title);
    }
}

@Component
public class InputSanitizer {
    
    public String sanitize(String input) {
        
        if (input == null) {
            return null;
        }
        
        // Remove SQL keywords
        String sanitized = input
            .replaceAll("(?i)\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\\b", "")
            .replaceAll("[';\"\\-\\-]", "");  // Remove special chars
        
        // Limit length
        if (sanitized.length() > 100) {
            sanitized = sanitized.substring(0, 100);
        }
        
        return sanitized.trim();
    }
}
```

---

## Key Takeaways:

```
Q46: PCI Compliance
✅ Never store card data (use Stripe tokens)
✅ Store only: last 4 digits, brand, token
✅ TLS 1.2+ for transmission
✅ Network segmentation

Q47: Scalping Prevention
✅ CAPTCHA for suspicious requests
✅ Rate limiting (5 bookings/hour/user)
✅ Device fingerprinting (10/day/device)
✅ Velocity checks (3 bookings/5min)
✅ Max 10 seats per transaction
✅ Phone verification for >₹5000

Q48: GDPR Compliance
✅ Right to deletion (anonymize, don't hard delete)
✅ Right to export (JSON + ZIP download)
✅ 90-day soft delete, then hard delete
✅ 7-year retention for financial records

Q49: Authentication
✅ JWT access token (15 min expiry)
✅ Refresh token (7 day expiry)
✅ Role-based access control
✅ Token revocation on logout

Q50: SQL Injection Prevention
✅ Always use parameterized queries
✅ Never concatenate user input
✅ Input validation (regex)
✅ Use JPA/Criteria API
```

This demonstrates production security expertise! 🎯
