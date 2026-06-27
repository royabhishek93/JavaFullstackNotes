# Q49: Authentication & Authorization - JWT tokens, session management

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: JWT + Refresh Tokens

```java
@Service
public class AuthenticationService {
    
    private final String JWT_SECRET = System.getenv("JWT_SECRET");
    private final long ACCESS_TOKEN_EXPIRY = 15 * 60 * 1000;  // 15 minutes
    private final long REFRESH_TOKEN_EXPIRY = 7 * 24 * 60 * 60 * 1000;  // 7 days
    
    public AuthenticationResponse login(LoginRequest request) {
        
        // Step 1: Validate credentials
        User user = userRepository.findByEmail(request.getEmail())
            .orElseThrow(() -> new InvalidCredentialsException());
        
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new InvalidCredentialsException();
        }
        
        // Step 2: Check account status
        if (!user.isActive()) {
            throw new AccountDisabledException();
        }
        
        // Step 3: Generate access token
        String accessToken = generateAccessToken(user);
        
        // Step 4: Generate refresh token
        String refreshToken = generateRefreshToken(user);
        
        // Step 5: Store refresh token
        RefreshToken token = RefreshToken.builder()
            .token(refreshToken)
            .userId(user.getId())
            .expiresAt(LocalDateTime.now().plusDays(7))
            .build();
        
        refreshTokenRepository.save(token);
        
        // Step 6: Update last login
        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);
        
        return AuthenticationResponse.builder()
            .accessToken(accessToken)
            .refreshToken(refreshToken)
            .expiresIn(ACCESS_TOKEN_EXPIRY)
            .tokenType("Bearer")
            .build();
    }
    
    private String generateAccessToken(User user) {
        
        Date now = new Date();
        Date expiry = new Date(now.getTime() + ACCESS_TOKEN_EXPIRY);
        
        return Jwts.builder()
            .setSubject(String.valueOf(user.getId()))
            .claim("email", user.getEmail())
            .claim("role", user.getRole())
            .setIssuedAt(now)
            .setExpiresAt(expiry)
            .signWith(SignatureAlgorithm.HS512, JWT_SECRET)
            .compact();
    }
    
    private String generateRefreshToken(User user) {
        
        Date now = new Date();
        Date expiry = new Date(now.getTime() + REFRESH_TOKEN_EXPIRY);
        
        return Jwts.builder()
            .setSubject(String.valueOf(user.getId()))
            .setIssuedAt(now)
            .setExpiresAt(expiry)
            .signWith(SignatureAlgorithm.HS512, JWT_SECRET)
            .compact();
    }
    
    public AuthenticationResponse refreshToken(String refreshToken) {
        
        // Step 1: Validate refresh token
        Claims claims = Jwts.parser()
            .setSigningKey(JWT_SECRET)
            .parseClaimsJws(refreshToken)
            .getBody();
        
        Long userId = Long.parseLong(claims.getSubject());
        
        // Step 2: Check if token exists in database
        RefreshToken storedToken = refreshTokenRepository
            .findByToken(refreshToken)
            .orElseThrow(() -> new InvalidTokenException());
        
        if (storedToken.isRevoked() || 
            storedToken.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new InvalidTokenException();
        }
        
        // Step 3: Generate new access token
        User user = userRepository.findById(userId).orElseThrow();
        String newAccessToken = generateAccessToken(user);
        
        return AuthenticationResponse.builder()
            .accessToken(newAccessToken)
            .refreshToken(refreshToken)  // Keep same refresh token
            .expiresIn(ACCESS_TOKEN_EXPIRY)
            .tokenType("Bearer")
            .build();
    }
    
    public void logout(String refreshToken) {
        
        // Revoke refresh token
        refreshTokenRepository.findByToken(refreshToken)
            .ifPresent(token -> {
                token.setRevoked(true);
                refreshTokenRepository.save(token);
            });
    }
}

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    
    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        
        // Extract token from Authorization header
        String header = request.getHeader("Authorization");
        
        if (header == null || !header.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }
        
        String token = header.substring(7);
        
        try {
            // Validate token
            Claims claims = Jwts.parser()
                .setSigningKey(JWT_SECRET)
                .parseClaimsJws(token)
                .getBody();
            
            Long userId = Long.parseLong(claims.getSubject());
            String role = claims.get("role", String.class);
            
            // Set authentication context
            UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(
                    userId,
                    null,
                    List.of(new SimpleGrantedAuthority(role))
                );
            
            SecurityContextHolder.getContext()
                .setAuthentication(authentication);
            
        } catch (ExpiredJwtException e) {
            response.setStatus(401);
            response.getWriter().write("{\"error\": \"Token expired\"}");
            return;
        } catch (Exception e) {
            response.setStatus(401);
            response.getWriter().write("{\"error\": \"Invalid token\"}");
            return;
        }
        
        filterChain.doFilter(request, response);
    }
}
```

**Authorization (Role-Based Access Control):**

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) 
            throws Exception {
        
        http.csrf().disable()
            .authorizeRequests()
                // Public endpoints
                .antMatchers("/api/auth/**").permitAll()
                .antMatchers("/api/movies/**").permitAll()
                .antMatchers("/api/shows/search").permitAll()
                
                // User endpoints
                .antMatchers("/api/bookings/**").hasRole("USER")
                .antMatchers("/api/payments/**").hasRole("USER")
                
                // Admin endpoints
                .antMatchers("/api/admin/**").hasRole("ADMIN")
                .antMatchers("/actuator/**").hasRole("ADMIN")
                
                // All other requests require authentication
                .anyRequest().authenticated()
            .and()
            .sessionManagement()
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            .and()
            .addFilterBefore(
                jwtAuthenticationFilter,
                UsernamePasswordAuthenticationFilter.class
            );
        
        return http.build();
    }
}
```

---
