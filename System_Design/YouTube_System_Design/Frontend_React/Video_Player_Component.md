# Video Player Component - React.js Implementation

## Table of Contents
1. [Project Setup](#project-setup)
2. [Video Player Component](#video-player-component)
3. [Video Upload Component](#video-upload-component)
4. [Video Feed Component](#video-feed-component)
5. [State Management](#state-management)
6. [API Service](#api-service)

---

## Project Setup

### Dependencies (package.json)

```json
{
  "name": "youtube-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "video.js": "^8.6.1",
    "react-player": "^2.13.0",
    "@tanstack/react-query": "^5.12.0",
    "zustand": "^4.4.7",
    "react-dropzone": "^14.2.3",
    "react-icons": "^4.12.0",
    "tailwindcss": "^3.3.5",
    "typescript": "^5.3.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.42",
    "@types/video.js": "^7.3.57",
    "vite": "^5.0.0"
  }
}
```

### Install Dependencies

```bash
npm install
```

---

## Video Player Component

### VideoPlayer.tsx

```tsx
import React, { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import Player from 'video.js/dist/types/player';

interface VideoPlayerProps {
  videoId: string;
  videoUrl: string;
  thumbnailUrl?: string;
  onViewIncrement?: () => void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoId,
  videoUrl,
  thumbnailUrl,
  onViewIncrement
}) => {
  const videoRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<Player | null>(null);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    // Initialize Video.js player
    if (!playerRef.current && videoRef.current) {
      const videoElement = document.createElement('video-js');
      videoElement.classList.add('vjs-big-play-centered');
      videoRef.current.appendChild(videoElement);

      const player = videojs(videoElement, {
        autoplay: false,
        controls: true,
        responsive: true,
        fluid: true,
        preload: 'auto',
        poster: thumbnailUrl,
        sources: [
          {
            src: videoUrl,
            type: 'video/mp4'
          }
        ],
        // Quality selector for adaptive bitrate
        controlBar: {
          children: [
            'playToggle',
            'volumePanel',
            'currentTimeDisplay',
            'timeDivider',
            'durationDisplay',
            'progressControl',
            'remainingTimeDisplay',
            'qualitySelector',
            'fullscreenToggle'
          ]
        }
      });

      playerRef.current = player;

      // Increment view count when video starts playing
      player.on('play', () => {
        if (!hasStarted) {
          setHasStarted(true);
          onViewIncrement?.();
        }
      });

      // Save watch position every 10 seconds
      player.on('timeupdate', () => {
        const currentTime = player.currentTime();
        if (currentTime && currentTime % 10 === 0) {
          localStorage.setItem(`video-${videoId}-position`, currentTime.toString());
        }
      });

      // Resume from last position
      const savedPosition = localStorage.getItem(`video-${videoId}-position`);
      if (savedPosition) {
        player.currentTime(parseFloat(savedPosition));
      }
    }

    // Cleanup on unmount
    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [videoId, videoUrl, thumbnailUrl, onViewIncrement, hasStarted]);

  return (
    <div className="w-full">
      <div ref={videoRef} className="video-container" />
      <style jsx>{`
        .video-container {
          max-width: 100%;
          aspect-ratio: 16/9;
        }
        
        .video-js {
          width: 100%;
          height: 100%;
        }
      `}</style>
    </div>
  );
};

export default VideoPlayer;
```

---

### Alternative: ReactPlayer Component (Simpler)

```tsx
import React, { useState } from 'react';
import ReactPlayer from 'react-player';

interface SimpleVideoPlayerProps {
  videoUrl: string;
  thumbnailUrl?: string;
  onViewIncrement?: () => void;
}

const SimpleVideoPlayer: React.FC<SimpleVideoPlayerProps> = ({
  videoUrl,
  thumbnailUrl,
  onViewIncrement
}) => {
  const [hasStarted, setHasStarted] = useState(false);

  const handleStart = () => {
    if (!hasStarted) {
      setHasStarted(true);
      onViewIncrement?.();
    }
  };

  return (
    <div className="relative w-full aspect-video bg-black">
      <ReactPlayer
        url={videoUrl}
        controls
        width="100%"
        height="100%"
        light={thumbnailUrl}
        playing={false}
        onStart={handleStart}
        config={{
          file: {
            attributes: {
              controlsList: 'nodownload'
            }
          }
        }}
      />
    </div>
  );
};

export default SimpleVideoPlayer;
```

---

## Video Upload Component

### VideoUpload.tsx

```tsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { FiUploadCloud, FiCheckCircle, FiXCircle } from 'react-icons/fi';

interface VideoUploadProps {
  userId: string;
  onUploadSuccess?: (videoId: string) => void;
}

interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ userId, onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Dropzone configuration
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setTitle(acceptedFiles[0].name.replace(/\.[^/.]+$/, '')); // Remove extension
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv']
    },
    maxFiles: 1,
    maxSize: 2 * 1024 * 1024 * 1024 // 2GB
  });

  // Step 1: Upload video file to S3 (presigned URL)
  const uploadToS3 = async (file: File): Promise<string> => {
    // Get presigned URL from backend
    const { data } = await axios.post('/api/v1/videos/upload-url', {
      fileName: file.name,
      contentType: file.type
    });

    const { uploadUrl, videoUrl } = data;

    // Upload to S3 with progress tracking
    await axios.put(uploadUrl, file, {
      headers: {
        'Content-Type': file.type
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          setUploadProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total)
          });
        }
      }
    });

    return videoUrl;
  };

  // Step 2: Create video metadata in database
  const createVideoMetadata = async (videoUrl: string) => {
    const response = await axios.post('/api/v1/videos', {
      title,
      description,
      videoUrl,
      duration: 0, // Will be extracted by backend
      category,
      tags: tags.split(',').map(tag => tag.trim()),
      language: 'en',
      isPublic: true
    }, {
      headers: {
        'X-User-Id': userId
      }
    });

    return response.data;
  };

  const handleUpload = async () => {
    if (!file || !title) {
      setErrorMessage('Please select a file and provide a title');
      return;
    }

    setIsUploading(true);
    setUploadStatus('uploading');
    setErrorMessage('');

    try {
      // Step 1: Upload video to S3
      const videoUrl = await uploadToS3(file);

      // Step 2: Create video metadata
      const videoData = await createVideoMetadata(videoUrl);

      setUploadStatus('success');
      setIsUploading(false);
      onUploadSuccess?.(videoData.id);

      // Reset form
      setTimeout(() => {
        setFile(null);
        setTitle('');
        setDescription('');
        setCategory('');
        setTags('');
        setUploadProgress(null);
        setUploadStatus('idle');
      }, 3000);

    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus('error');
      setErrorMessage('Upload failed. Please try again.');
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Upload Video</h2>

      {/* File Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${file ? 'bg-green-50 border-green-500' : ''}`}
      >
        <input {...getInputProps()} />
        <FiUploadCloud className="mx-auto text-6xl text-gray-400 mb-4" />
        {!file ? (
          <>
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? 'Drop video here' : 'Drag & drop video, or click to select'}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Supported formats: MP4, MOV, AVI, MKV (Max 2GB)
            </p>
          </>
        ) : (
          <div className="flex items-center justify-center gap-2">
            <FiCheckCircle className="text-green-500 text-2xl" />
            <p className="text-lg font-medium text-gray-700">{file.name}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="ml-4 text-red-500 hover:text-red-700"
            >
              <FiXCircle className="text-xl" />
            </button>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {uploadProgress && (
        <div className="mt-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Uploading...</span>
            <span>{uploadProgress.percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Video Details Form */}
      {file && !isUploading && (
        <div className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter video title"
              maxLength={100}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Tell viewers about your video"
              maxLength={5000}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select category</option>
                <option value="education">Education</option>
                <option value="entertainment">Entertainment</option>
                <option value="music">Music</option>
                <option value="gaming">Gaming</option>
                <option value="technology">Technology</option>
                <option value="sports">Sports</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="system design, interview"
              />
            </div>
          </div>

          {errorMessage && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {errorMessage}
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!title || isUploading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-6 rounded-lg transition-colors"
          >
            {isUploading ? 'Uploading...' : 'Publish Video'}
          </button>
        </div>
      )}

      {/* Success Message */}
      {uploadStatus === 'success' && (
        <div className="mt-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded flex items-center gap-2">
          <FiCheckCircle className="text-xl" />
          <span>Video uploaded successfully! Processing will complete shortly.</span>
        </div>
      )}
    </div>
  );
};

export default VideoUpload;
```

---

## Video Feed Component (Infinite Scroll)

### VideoFeed.tsx

```tsx
import React, { useEffect, useRef } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import axios from 'axios';
import VideoCard from './VideoCard';

interface Video {
  id: string;
  title: string;
  thumbnailUrl: string;
  duration: number;
  views: number;
  createdAt: string;
  userId: string;
  username: string;
}

const fetchVideos = async ({ pageParam = 0 }): Promise<{ videos: Video[]; nextPage: number | undefined }> => {
  const { data } = await axios.get(`/api/v1/videos?page=${pageParam}&size=20`);
  return {
    videos: data.content,
    nextPage: data.last ? undefined : pageParam + 1
  };
};

const VideoFeed: React.FC = () => {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError
  } = useInfiniteQuery({
    queryKey: ['videos'],
    queryFn: fetchVideos,
    getNextPageParam: (lastPage) => lastPage.nextPage,
    initialPageParam: 0
  });

  // Intersection Observer for infinite scroll
  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();

    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    });

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
        {[...Array(12)].map((_, i) => (
          <VideoCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 text-lg">Failed to load videos. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {data?.pages.map((page) =>
          page.videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))
        )}
      </div>

      {/* Load More Trigger */}
      <div ref={loadMoreRef} className="h-10 flex items-center justify-center mt-8">
        {isFetchingNextPage && <span className="text-gray-500">Loading more videos...</span>}
      </div>
    </div>
  );
};

const VideoCardSkeleton: React.FC = () => (
  <div className="animate-pulse">
    <div className="bg-gray-300 aspect-video rounded-lg mb-2" />
    <div className="h-4 bg-gray-300 rounded w-3/4 mb-2" />
    <div className="h-3 bg-gray-300 rounded w-1/2" />
  </div>
);

export default VideoFeed;
```

### VideoCard.tsx

```tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

interface VideoCardProps {
  video: {
    id: string;
    title: string;
    thumbnailUrl: string;
    duration: number;
    views: number;
    createdAt: string;
    username: string;
  };
}

const VideoCard: React.FC<VideoCardProps> = ({ video }) => {
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViews = (views: number): string => {
    if (views >= 1000000) return `${(views / 1000000).toFixed(1)}M`;
    if (views >= 1000) return `${(views / 1000).toFixed(1)}K`;
    return views.toString();
  };

  return (
    <Link to={`/watch?v=${video.id}`} className="group">
      <div className="relative aspect-video overflow-hidden rounded-lg bg-gray-200">
        <img
          src={video.thumbnailUrl}
          alt={video.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
          loading="lazy"
        />
        <div className="absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1.5 py-0.5 rounded">
          {formatDuration(video.duration)}
        </div>
      </div>

      <div className="mt-2">
        <h3 className="font-medium text-sm line-clamp-2 group-hover:text-blue-600">
          {video.title}
        </h3>
        <p className="text-xs text-gray-600 mt-1">{video.username}</p>
        <p className="text-xs text-gray-600">
          {formatViews(video.views)} views • {formatDistanceToNow(new Date(video.createdAt), { addSuffix: true })}
        </p>
      </div>
    </Link>
  );
};

export default VideoCard;
```

---

## State Management (Zustand)

### videoStore.ts

```typescript
import { create } from 'zustand';

interface Video {
  id: string;
  title: string;
  videoUrl: string;
  thumbnailUrl: string;
  duration: number;
  views: number;
  likes: number;
}

interface VideoStore {
  currentVideo: Video | null;
  setCurrentVideo: (video: Video) => void;
  incrementViews: (videoId: string) => void;
  incrementLikes: (videoId: string) => void;
}

export const useVideoStore = create<VideoStore>((set) => ({
  currentVideo: null,
  setCurrentVideo: (video) => set({ currentVideo: video }),
  incrementViews: (videoId) =>
    set((state) => ({
      currentVideo:
        state.currentVideo?.id === videoId
          ? { ...state.currentVideo, views: state.currentVideo.views + 1 }
          : state.currentVideo
    })),
  incrementLikes: (videoId) =>
    set((state) => ({
      currentVideo:
        state.currentVideo?.id === videoId
          ? { ...state.currentVideo, likes: state.currentVideo.likes + 1 }
          : state.currentVideo
    }))
}));
```

---

## API Service

### videoApi.ts

```typescript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081/api/v1';

export const videoApi = {
  getVideo: async (videoId: string) => {
    const { data } = await axios.get(`${API_BASE_URL}/videos/${videoId}`);
    return data;
  },

  getVideos: async (page: number = 0, size: number = 20) => {
    const { data } = await axios.get(`${API_BASE_URL}/videos`, {
      params: { page, size }
    });
    return data;
  },

  searchVideos: async (query: string, page: number = 0) => {
    const { data } = await axios.get(`${API_BASE_URL}/videos/search`, {
      params: { q: query, page, size: 20 }
    });
    return data;
  },

  getTrendingVideos: async () => {
    const { data } = await axios.get(`${API_BASE_URL}/videos/trending`);
    return data;
  },

  incrementViews: async (videoId: string) => {
    await axios.post(`${API_BASE_URL}/videos/${videoId}/views`);
  },

  likeVideo: async (videoId: string, userId: string) => {
    await axios.post(`${API_BASE_URL}/videos/${videoId}/like`, null, {
      headers: { 'X-User-Id': userId }
    });
  }
};
```

---

## Next Steps
- [AWS Deployment Guide](../AWS_Deployment/AWS_Architecture.md)
- [Complete System Flow](../Flows/Video_Streaming_Flow.md)
