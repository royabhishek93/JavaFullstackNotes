# Video Service - Java Spring Boot Implementation

## Table of Contents
1. [Project Structure](#project-structure)
2. [Dependencies](#dependencies)
3. [Entity Classes](#entity-classes)
4. [Repository Layer](#repository-layer)
5. [Service Layer](#service-layer)
6. [Controller Layer](#controller-layer)
7. [Kafka Integration](#kafka-integration)
8. [Redis Caching](#redis-caching)

---

## Project Structure

```
video-service/
├── src/main/java/com/youtube/video/
│   ├── VideoServiceApplication.java
│   ├── config/
│   │   ├── KafkaConfig.java
│   │   ├── RedisConfig.java
│   │   └── S3Config.java
│   ├── controller/
│   │   └── VideoController.java
│   ├── service/
│   │   ├── VideoService.java
│   │   └── VideoServiceImpl.java
│   ├── repository/
│   │   └── VideoRepository.java
│   ├── entity/
│   │   ├── Video.java
│   │   └── VideoQuality.java
│   ├── dto/
│   │   ├── VideoUploadRequest.java
│   │   ├── VideoResponse.java
│   │   └── VideoUpdateRequest.java
│   └── kafka/
│       └── VideoEventProducer.java
└── src/main/resources/
    └── application.yml
```

---

## Dependencies (pom.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>
    
    <groupId>com.youtube</groupId>
    <artifactId>video-service</artifactId>
    <version>1.0.0</version>
    
    <properties>
        <java.version>17</java.version>
    </properties>
    
    <dependencies>
        <!-- Spring Boot Web -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        
        <!-- Spring Data JPA -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        
        <!-- PostgreSQL Driver -->
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        
        <!-- Redis -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
        </dependency>
        
        <!-- Kafka -->
        <dependency>
            <groupId>org.springframework.kafka</groupId>
            <artifactId>spring-kafka</artifactId>
        </dependency>
        
        <!-- AWS S3 SDK -->
        <dependency>
            <groupId>software.amazon.awssdk</groupId>
            <artifactId>s3</artifactId>
            <version>2.20.0</version>
        </dependency>
        
        <!-- Lombok (Reduce Boilerplate) -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        
        <!-- Validation -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        
        <!-- JWT for Authentication -->
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>0.11.5</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-impl</artifactId>
            <version>0.11.5</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-jackson</artifactId>
            <version>0.11.5</version>
            <scope>runtime</scope>
        </dependency>
    </dependencies>
</project>
```

---

## Entity Classes

### Video.java

```java
package com.youtube.video.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "videos", indexes = {
    @Index(name = "idx_user_id", columnList = "user_id"),
    @Index(name = "idx_status", columnList = "status"),
    @Index(name = "idx_created_at", columnList = "created_at"),
    @Index(name = "idx_views", columnList = "views")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Video {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "user_id", nullable = false)
    private Long userId;
    
    @Column(nullable = false, length = 255)
    private String title;
    
    @Column(columnDefinition = "TEXT")
    private String description;
    
    @Column(name = "video_url", nullable = false, length = 500)
    private String videoUrl;  // S3 URL
    
    @Column(name = "thumbnail_url", length = 500)
    private String thumbnailUrl;
    
    @Column(nullable = false)
    private Integer duration;  // seconds
    
    @Column(nullable = false)
    @Builder.Default
    private Long views = 0L;
    
    @Column(nullable = false)
    @Builder.Default
    private Integer likes = 0;
    
    @Column(nullable = false)
    @Builder.Default
    private Integer dislikes = 0;
    
    @Enumerated(EnumType.STRING)
    @Column(length = 20, nullable = false)
    @Builder.Default
    private VideoStatus status = VideoStatus.PROCESSING;
    
    @Column(length = 50)
    private String category;
    
    @Column(columnDefinition = "text[]")
    private String[] tags;
    
    @Column(length = 10)
    private String language;
    
    @Column(name = "is_public", nullable = false)
    @Builder.Default
    private Boolean isPublic = true;
    
    @OneToMany(mappedBy = "video", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<VideoQuality> qualities = new ArrayList<>();
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    public enum VideoStatus {
        PROCESSING,
        READY,
        FAILED
    }
}
```

### VideoQuality.java

```java
package com.youtube.video.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "video_qualities", 
       uniqueConstraints = @UniqueConstraint(columnNames = {"video_id", "quality"}))
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class VideoQuality {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "video_id", nullable = false)
    private Video video;
    
    @Column(nullable = false, length = 10)
    private String quality;  // 144p, 360p, 720p, 1080p, 4K
    
    @Column(nullable = false, length = 500)
    private String url;  // S3 URL
    
    @Column(name = "file_size", nullable = false)
    private Long fileSize;  // bytes
    
    private Integer bitrate;  // kbps
    
    @Column(length = 20)
    private String codec;
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
```

---

## Repository Layer

### VideoRepository.java

```java
package com.youtube.video.repository;

import com.youtube.video.entity.Video;
import com.youtube.video.entity.Video.VideoStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface VideoRepository extends JpaRepository<Video, Long> {
    
    // Find by user
    Page<Video> findByUserId(Long userId, Pageable pageable);
    
    // Find by status
    List<Video> findByStatus(VideoStatus status);
    
    // Find public videos
    Page<Video> findByIsPublicTrue(Pageable pageable);
    
    // Find by category
    Page<Video> findByCategory(String category, Pageable pageable);
    
    // Search by title (case-insensitive)
    @Query("SELECT v FROM Video v WHERE LOWER(v.title) LIKE LOWER(CONCAT('%', :keyword, '%')) " +
           "AND v.isPublic = true")
    Page<Video> searchByTitle(@Param("keyword") String keyword, Pageable pageable);
    
    // Trending videos (most views in last 7 days)
    @Query("SELECT v FROM Video v WHERE v.createdAt > :since AND v.isPublic = true " +
           "ORDER BY v.views DESC")
    Page<Video> findTrendingVideos(@Param("since") LocalDateTime since, Pageable pageable);
    
    // Increment view count (optimized)
    @Modifying
    @Query("UPDATE Video v SET v.views = v.views + 1 WHERE v.id = :videoId")
    int incrementViewCount(@Param("videoId") Long videoId);
    
    // Increment like count
    @Modifying
    @Query("UPDATE Video v SET v.likes = v.likes + 1 WHERE v.id = :videoId")
    int incrementLikeCount(@Param("videoId") Long videoId);
    
    // Decrement like count
    @Modifying
    @Query("UPDATE Video v SET v.likes = v.likes - 1 WHERE v.id = :videoId AND v.likes > 0")
    int decrementLikeCount(@Param("videoId") Long videoId);
    
    // Get total views for a user
    @Query("SELECT COALESCE(SUM(v.views), 0) FROM Video v WHERE v.userId = :userId")
    Long getTotalViewsByUser(@Param("userId") Long userId);
}
```

---

## Service Layer

### VideoService.java (Interface)

```java
package com.youtube.video.service;

import com.youtube.video.dto.VideoResponse;
import com.youtube.video.dto.VideoUploadRequest;
import com.youtube.video.dto.VideoUpdateRequest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface VideoService {
    VideoResponse uploadVideo(VideoUploadRequest request, Long userId);
    VideoResponse getVideoById(Long videoId);
    Page<VideoResponse> getVideosByUser(Long userId, Pageable pageable);
    Page<VideoResponse> searchVideos(String keyword, Pageable pageable);
    Page<VideoResponse> getTrendingVideos(Pageable pageable);
    VideoResponse updateVideo(Long videoId, VideoUpdateRequest request, Long userId);
    void deleteVideo(Long videoId, Long userId);
    void incrementViewCount(Long videoId);
    void incrementLikeCount(Long videoId, Long userId);
}
```

### VideoServiceImpl.java

```java
package com.youtube.video.service;

import com.youtube.video.dto.VideoResponse;
import com.youtube.video.dto.VideoUploadRequest;
import com.youtube.video.dto.VideoUpdateRequest;
import com.youtube.video.entity.Video;
import com.youtube.video.kafka.VideoEventProducer;
import com.youtube.video.repository.VideoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
@Slf4j
public class VideoServiceImpl implements VideoService {
    
    private final VideoRepository videoRepository;
    private final VideoEventProducer videoEventProducer;
    
    @Override
    @Transactional
    public VideoResponse uploadVideo(VideoUploadRequest request, Long userId) {
        log.info("Uploading video: {} by user: {}", request.getTitle(), userId);
        
        // Create video entity
        Video video = Video.builder()
                .userId(userId)
                .title(request.getTitle())
                .description(request.getDescription())
                .videoUrl(request.getVideoUrl())
                .thumbnailUrl(request.getThumbnailUrl())
                .duration(request.getDuration())
                .category(request.getCategory())
                .tags(request.getTags())
                .language(request.getLanguage())
                .isPublic(request.getIsPublic())
                .status(Video.VideoStatus.PROCESSING)
                .build();
        
        // Save to database
        Video savedVideo = videoRepository.save(video);
        
        // Publish event to Kafka for video processing
        videoEventProducer.sendVideoUploadEvent(savedVideo.getId(), userId, request.getVideoUrl());
        
        log.info("Video uploaded successfully: {}", savedVideo.getId());
        return mapToResponse(savedVideo);
    }
    
    @Override
    @Cacheable(value = "videos", key = "#videoId")
    public VideoResponse getVideoById(Long videoId) {
        log.info("Fetching video: {}", videoId);
        
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new RuntimeException("Video not found: " + videoId));
        
        return mapToResponse(video);
    }
    
    @Override
    public Page<VideoResponse> getVideosByUser(Long userId, Pageable pageable) {
        log.info("Fetching videos for user: {}", userId);
        return videoRepository.findByUserId(userId, pageable)
                .map(this::mapToResponse);
    }
    
    @Override
    public Page<VideoResponse> searchVideos(String keyword, Pageable pageable) {
        log.info("Searching videos with keyword: {}", keyword);
        return videoRepository.searchByTitle(keyword, pageable)
                .map(this::mapToResponse);
    }
    
    @Override
    @Cacheable(value = "trending", key = "'videos'")
    public Page<VideoResponse> getTrendingVideos(Pageable pageable) {
        log.info("Fetching trending videos");
        LocalDateTime sevenDaysAgo = LocalDateTime.now().minusDays(7);
        return videoRepository.findTrendingVideos(sevenDaysAgo, pageable)
                .map(this::mapToResponse);
    }
    
    @Override
    @Transactional
    @CacheEvict(value = "videos", key = "#videoId")
    public VideoResponse updateVideo(Long videoId, VideoUpdateRequest request, Long userId) {
        log.info("Updating video: {} by user: {}", videoId, userId);
        
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new RuntimeException("Video not found: " + videoId));
        
        // Verify ownership
        if (!video.getUserId().equals(userId)) {
            throw new RuntimeException("Unauthorized: User does not own this video");
        }
        
        // Update fields
        if (request.getTitle() != null) {
            video.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            video.setDescription(request.getDescription());
        }
        if (request.getThumbnailUrl() != null) {
            video.setThumbnailUrl(request.getThumbnailUrl());
        }
        if (request.getCategory() != null) {
            video.setCategory(request.getCategory());
        }
        if (request.getTags() != null) {
            video.setTags(request.getTags());
        }
        if (request.getIsPublic() != null) {
            video.setIsPublic(request.getIsPublic());
        }
        
        Video updatedVideo = videoRepository.save(video);
        log.info("Video updated successfully: {}", videoId);
        
        return mapToResponse(updatedVideo);
    }
    
    @Override
    @Transactional
    @CacheEvict(value = "videos", key = "#videoId")
    public void deleteVideo(Long videoId, Long userId) {
        log.info("Deleting video: {} by user: {}", videoId, userId);
        
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new RuntimeException("Video not found: " + videoId));
        
        // Verify ownership
        if (!video.getUserId().equals(userId)) {
            throw new RuntimeException("Unauthorized: User does not own this video");
        }
        
        videoRepository.delete(video);
        log.info("Video deleted successfully: {}", videoId);
    }
    
    @Override
    @Transactional
    public void incrementViewCount(Long videoId) {
        int updated = videoRepository.incrementViewCount(videoId);
        if (updated == 0) {
            throw new RuntimeException("Failed to increment view count for video: " + videoId);
        }
    }
    
    @Override
    @Transactional
    public void incrementLikeCount(Long videoId, Long userId) {
        // In production, check if user already liked (from likes table)
        int updated = videoRepository.incrementLikeCount(videoId);
        if (updated == 0) {
            throw new RuntimeException("Failed to increment like count for video: " + videoId);
        }
    }
    
    private VideoResponse mapToResponse(Video video) {
        return VideoResponse.builder()
                .id(video.getId())
                .userId(video.getUserId())
                .title(video.getTitle())
                .description(video.getDescription())
                .videoUrl(video.getVideoUrl())
                .thumbnailUrl(video.getThumbnailUrl())
                .duration(video.getDuration())
                .views(video.getViews())
                .likes(video.getLikes())
                .dislikes(video.getDislikes())
                .status(video.getStatus().name())
                .category(video.getCategory())
                .tags(video.getTags())
                .language(video.getLanguage())
                .isPublic(video.getIsPublic())
                .createdAt(video.getCreatedAt())
                .updatedAt(video.getUpdatedAt())
                .build();
    }
}
```

---

## Controller Layer

### VideoController.java

```java
package com.youtube.video.controller;

import com.youtube.video.dto.VideoResponse;
import com.youtube.video.dto.VideoUploadRequest;
import com.youtube.video.dto.VideoUpdateRequest;
import com.youtube.video.service.VideoService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/videos")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")  // Configure properly in production
public class VideoController {
    
    private final VideoService videoService;
    
    /**
     * Upload a new video
     * POST /api/v1/videos
     */
    @PostMapping
    public ResponseEntity<VideoResponse> uploadVideo(
            @Valid @RequestBody VideoUploadRequest request,
            @RequestHeader("X-User-Id") Long userId) {
        
        VideoResponse response = videoService.uploadVideo(request, userId);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
    
    /**
     * Get video by ID
     * GET /api/v1/videos/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<VideoResponse> getVideo(@PathVariable Long id) {
        VideoResponse response = videoService.getVideoById(id);
        return ResponseEntity.ok(response);
    }
    
    /**
     * Get videos by user
     * GET /api/v1/videos/user/{userId}?page=0&size=20
     */
    @GetMapping("/user/{userId}")
    public ResponseEntity<Page<VideoResponse>> getVideosByUser(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Pageable pageable = PageRequest.of(page, size, Sort.by("createdAt").descending());
        Page<VideoResponse> videos = videoService.getVideosByUser(userId, pageable);
        return ResponseEntity.ok(videos);
    }
    
    /**
     * Search videos
     * GET /api/v1/videos/search?q=system+design&page=0&size=20
     */
    @GetMapping("/search")
    public ResponseEntity<Page<VideoResponse>> searchVideos(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Pageable pageable = PageRequest.of(page, size);
        Page<VideoResponse> videos = videoService.searchVideos(q, pageable);
        return ResponseEntity.ok(videos);
    }
    
    /**
     * Get trending videos
     * GET /api/v1/videos/trending?page=0&size=20
     */
    @GetMapping("/trending")
    public ResponseEntity<Page<VideoResponse>> getTrendingVideos(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Pageable pageable = PageRequest.of(page, size);
        Page<VideoResponse> videos = videoService.getTrendingVideos(pageable);
        return ResponseEntity.ok(videos);
    }
    
    /**
     * Update video
     * PUT /api/v1/videos/{id}
     */
    @PutMapping("/{id}")
    public ResponseEntity<VideoResponse> updateVideo(
            @PathVariable Long id,
            @Valid @RequestBody VideoUpdateRequest request,
            @RequestHeader("X-User-Id") Long userId) {
        
        VideoResponse response = videoService.updateVideo(id, request, userId);
        return ResponseEntity.ok(response);
    }
    
    /**
     * Delete video
     * DELETE /api/v1/videos/{id}
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteVideo(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") Long userId) {
        
        videoService.deleteVideo(id, userId);
        return ResponseEntity.noContent().build();
    }
    
    /**
     * Increment view count
     * POST /api/v1/videos/{id}/views
     */
    @PostMapping("/{id}/views")
    public ResponseEntity<Void> incrementViews(@PathVariable Long id) {
        videoService.incrementViewCount(id);
        return ResponseEntity.ok().build();
    }
    
    /**
     * Like video
     * POST /api/v1/videos/{id}/like
     */
    @PostMapping("/{id}/like")
    public ResponseEntity<Void> likeVideo(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") Long userId) {
        
        videoService.incrementLikeCount(id, userId);
        return ResponseEntity.ok().build();
    }
}
```

---

## Kafka Integration

### VideoEventProducer.java

```java
package com.youtube.video.kafka;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class VideoEventProducer {
    
    private final KafkaTemplate<String, String> kafkaTemplate;
    private static final String VIDEO_UPLOAD_TOPIC = "video-upload-events";
    
    public void sendVideoUploadEvent(Long videoId, Long userId, String videoUrl) {
        String message = String.format("{\"videoId\": %d, \"userId\": %d, \"videoUrl\": \"%s\"}", 
                                       videoId, userId, videoUrl);
        
        kafkaTemplate.send(VIDEO_UPLOAD_TOPIC, videoId.toString(), message)
                .whenComplete((result, ex) -> {
                    if (ex == null) {
                        log.info("Video upload event sent: videoId={}", videoId);
                    } else {
                        log.error("Failed to send video upload event: videoId={}", videoId, ex);
                    }
                });
    }
}
```

---

## Redis Caching

### RedisConfig.java

```java
package com.youtube.video.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@Configuration
@EnableCaching
public class RedisConfig {
    
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(60))  // 60 minutes TTL
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));
        
        return RedisCacheManager.builder(connectionFactory)
                .cacheDefaults(config)
                .build();
    }
}
```

---

## Application Configuration

### application.yml

```yaml
spring:
  application:
    name: video-service
  
  datasource:
    url: jdbc:postgresql://localhost:5432/youtube
    username: postgres
    password: postgres
    driver-class-name: org.postgresql.Driver
  
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.PostgreSQLDialect
  
  redis:
    host: localhost
    port: 6379
  
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer

server:
  port: 8081

logging:
  level:
    com.youtube.video: DEBUG
```

---

## DTO Classes

### VideoUploadRequest.java

```java
package com.youtube.video.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class VideoUploadRequest {
    @NotBlank(message = "Title is required")
    private String title;
    
    private String description;
    
    @NotBlank(message = "Video URL is required")
    private String videoUrl;
    
    private String thumbnailUrl;
    
    @NotNull(message = "Duration is required")
    private Integer duration;
    
    private String category;
    private String[] tags;
    private String language;
    private Boolean isPublic = true;
}
```

### VideoResponse.java

```java
package com.youtube.video.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class VideoResponse {
    private Long id;
    private Long userId;
    private String title;
    private String description;
    private String videoUrl;
    private String thumbnailUrl;
    private Integer duration;
    private Long views;
    private Integer likes;
    private Integer dislikes;
    private String status;
    private String category;
    private String[] tags;
    private String language;
    private Boolean isPublic;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

---

## Testing with cURL

```bash
# Upload video
curl -X POST http://localhost:8081/api/v1/videos \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "title": "Learn System Design",
    "description": "Complete guide to system design interviews",
    "videoUrl": "https://s3.amazonaws.com/youtube-videos/video-123.mp4",
    "thumbnailUrl": "https://s3.amazonaws.com/youtube-videos/thumb-123.jpg",
    "duration": 300,
    "category": "education",
    "tags": ["system design", "interview"],
    "language": "en",
    "isPublic": true
  }'

# Get video
curl http://localhost:8081/api/v1/videos/1

# Search videos
curl "http://localhost:8081/api/v1/videos/search?q=system%20design&page=0&size=10"

# Increment views
curl -X POST http://localhost:8081/api/v1/videos/1/views
```

---

## Next Steps
- [React Frontend Implementation](../Frontend_React/Video_Player_Component.md)
- [AWS Deployment Guide](../AWS_Deployment/AWS_Architecture.md)
