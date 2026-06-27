# Video Streaming System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `video-streaming-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Video upload, processing, transcoding, and delivery
- Metadata, playlists, subscriptions, and watch history
- CDN-based playback and adaptive bitrate streaming
- Likes, views, recommendations, and moderation hooks
- Reliability, scale, and eventual consistency trade-offs

## One-line pitch
A production streaming system separates upload/processing from playback delivery, then scales metadata, CDN, and recommendation paths independently.
