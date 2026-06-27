# Database Schema Visual Guide - Video Streaming System

## Complete ER Diagram

```
┌────────────────────────────────────┐
│             USERS                  │
│────────────────────────────────────│
│ PK id (UUID)                       │
│    name                            │
│    email                           │
│    created_at                      │
└──────────────┬─────────────────────┘
               │ uploads
               ▼
┌────────────────────────────────────┐         ┌────────────────────────────────────┐
│             VIDEOS                 │         │           PLAYLISTS                │
│────────────────────────────────────│         │────────────────────────────────────│
│ PK id (UUID)                       │         │ PK id (UUID)                       │
│ FK creator_id -> users.id          │         │ FK owner_id -> users.id            │
│    title                           │         │    title                           │
│    description                     │         │    visibility                      │
│    visibility                      │         │    created_at                      │
│    status                          │         └──────────────┬─────────────────────┘
│    duration_sec                    │                        │ has many
│    created_at                      │                        ▼
└──────────────┬─────────────────────┘         ┌────────────────────────────────────┐
               │ has many                      │         PLAYLIST_ITEMS             │
               ▼                               │────────────────────────────────────│
┌────────────────────────────────────┐         │ PK id (UUID)                       │
│          VIDEO_ASSETS              │         │ FK playlist_id -> playlists.id     │
│────────────────────────────────────│         │ FK video_id -> videos.id           │
│ PK id (UUID)                       │         │    position                        │
│ FK video_id -> videos.id           │         │    created_at                      │
│    quality                         │         └────────────────────────────────────┘
│    codec                           │
│    manifest_url                    │         ┌────────────────────────────────────┐
│    storage_path                    │         │         SUBSCRIPTIONS              │
│    status                          │         │────────────────────────────────────│
│    created_at                      │         │ PK id (UUID)                       │
└────────────────────────────────────┘         │ FK subscriber_id -> users.id       │
                                               │ FK creator_id -> users.id          │
                                               │    created_at                      │
                                               └────────────────────────────────────┘

┌────────────────────────────────────┐         ┌────────────────────────────────────┐
│          WATCH_HISTORY             │         │           VIEW_EVENTS              │
│────────────────────────────────────│         │────────────────────────────────────│
│ PK id (UUID)                       │         │ PK id (UUID)                       │
│ FK user_id -> users.id             │         │ FK user_id -> users.id             │
│ FK video_id -> videos.id           │         │ FK video_id -> videos.id           │
│    progress_sec                    │         │    watch_time_sec                  │
│    last_watched_at                 │         │    created_at                      │
└────────────────────────────────────┘         └────────────────────────────────────┘
```

## Constraints
- UNIQUE `(playlist_id, video_id)` on `playlist_items` if duplicates not allowed
- UNIQUE `(subscriber_id, creator_id)` on `subscriptions`
- UNIQUE `(user_id, video_id)` on `watch_history` if one progress row per video

## Status Enums
- videos.status: UPLOADING, PROCESSING, READY, FAILED, BLOCKED
- videos.visibility: PUBLIC, PRIVATE, UNLISTED
- video_assets.status: PROCESSING, READY, FAILED
