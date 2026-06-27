# Designing a Video Streaming System (LLD)

## Requirements
1. Creators should upload videos and manage metadata.
2. System should transcode uploaded video into multiple bitrates/resolutions.
3. Users should stream videos with adaptive bitrate playback.
4. Support playlists, likes, comments, subscriptions, and watch history.
5. Track view counts and engagement analytics.
6. Support moderation, takedown, and visibility controls.
7. Scale reads globally using CDN.
8. Support near-real-time metadata updates with eventual consistency.

## Core Components
1. Upload Service
- Accepts creator upload request and stores raw video.

2. Media Processing Pipeline
- Generates thumbnails and HLS/DASH renditions.
- Produces manifests and segment files.

3. Metadata Service
- Stores title, description, tags, visibility, duration.

4. Playback Service
- Serves manifests, playback authorization, and CDN URLs.

5. Engagement Service
- Tracks likes, comments, subscriptions, views, and watch history.

6. Recommendation/Feed Service
- Builds home feed and related videos.

## Core Entities
1. Video
- id, creatorId, title, description, status, visibility, durationSec

2. VideoAsset
- id, videoId, quality, codec, manifestUrl, storagePath, status

3. Playlist
- id, ownerId, title, visibility

4. PlaylistItem
- playlistId, videoId, position

5. Subscription
- subscriberId, creatorId, createdAt

6. WatchHistory
- userId, videoId, progressSec, lastWatchedAt

7. ViewEvent
- id, userId, videoId, watchTimeSec, createdAt

## APIs
- POST /v1/videos/upload
- GET /v1/videos/{id}
- GET /v1/videos/{id}/playback
- POST /v1/videos/{id}/like
- POST /v1/playlists
- POST /v1/playlists/{id}/items
- GET /v1/feed/home

## Processing Flow
1. Creator uploads raw video.
2. Upload service stores raw object.
3. Processing pipeline transcodes and creates HLS/DASH renditions.
4. Metadata service marks video READY.
5. Playback service returns manifest URL via CDN.

## Playback Flow
1. User requests playback.
2. Playback auth validates region/subscription/visibility.
3. Manifest is served.
4. Player fetches adaptive segments from CDN.
5. View events are emitted asynchronously.

## State Transitions
- Video: UPLOADING -> PROCESSING -> READY or FAILED or BLOCKED
- Asset: PROCESSING -> READY or FAILED
- Playlist: ACTIVE or DELETED

## Interview One-Liner
Video streaming is really three systems: media pipeline, metadata platform, and global delivery path.
