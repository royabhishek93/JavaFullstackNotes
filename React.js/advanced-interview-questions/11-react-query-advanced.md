# How does React Query caching work? When do you use optimistic updates?

> **Interview priority:** SHOULD KNOW

## Question

How does React Query caching work? When do you use optimistic updates?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "React Query's cache is what sold me on it. Let me explain with a Twitter
> timeline. You open the app, your feed loads — that's a fetch. You switch
> to Notifications tab and come back to Home — should React fetch again?
> With React Query, that's a config decision, not an architecture decision."

```
REAL APP: Twitter/X Timeline — Cache Behavior

  SCENARIO: User opens feed, switches tabs, comes back

  Without React Query (manual useEffect):
  ──────────────────────────────────────
  useEffect(() => { fetchTweets(); }, []);
  // Every time component mounts → fetch
  // Switch tabs → component unmounts
  // Come back → component mounts → fetch again
  // User sees loading spinner every tab switch

  With React Query:
  ──────────────────────────────────────
  const { data } = useQuery({
    queryKey: ['timeline'],
    queryFn: fetchTimeline,
    staleTime: 30000,  // data is "fresh" for 30 seconds
    gcTime: 5 * 60 * 1000, // keep in memory for 5 minutes
  });

  CACHE LIFECYCLE:
  ┌──────────────────────────────────────────────────────────┐
  │  t=0:   Fetch runs → data cached as FRESH                 │
  │  t=30s: staleTime passes → data is now STALE              │
  │  t=35s: User switches to Notifications tab               │
  │         Component unmounts — but cache stays in memory    │
  │  t=50s: User switches back to Home tab                   │
  │         Component mounts → shows CACHED data instantly    │
  │         Triggers background refetch (data is stale)       │
  │         When refetch completes → silently updates UI      │
  │  t=5min: gcTime passes → cache entry removed from memory  │
  └──────────────────────────────────────────────────────────┘
  User sees instant data on tab switch, never a loading spinner ✅
```

```
OPTIMISTIC UPDATES — When to use:

  REAL APP: Twitter Like Button

  // SCENARIO: User likes a tweet
  // Network request takes 200-500ms
  // Without optimistic update: heart stays gray for 300ms then turns red
  // With optimistic update: heart turns red INSTANTLY

  const likeMutation = useMutation({
    mutationFn: (tweetId) => api.post(`/tweets/${tweetId}/like`),

    onMutate: async (tweetId) => {
      // 1. Cancel any in-flight queries for this tweet
      await queryClient.cancelQueries({ queryKey: ['tweet', tweetId] });

      // 2. Snapshot the current value (for rollback)
      const previousTweet = queryClient.getQueryData(['tweet', tweetId]);

      // 3. Optimistically update the cache
      queryClient.setQueryData(['tweet', tweetId], (old) => ({
        ...old,
        likes: old.likes + 1,
        isLiked: true,
      }));

      return { previousTweet }; // context for rollback
    },

    onError: (err, tweetId, context) => {
      // API call failed → roll back to previous state
      queryClient.setQueryData(['tweet', tweetId], context.previousTweet);
      showToast('Failed to like tweet. Try again.');
    },

    onSettled: (data, err, tweetId) => {
      // Always sync with server (whether success or error)
      queryClient.invalidateQueries({ queryKey: ['tweet', tweetId] });
    },
  });

  USE OPTIMISTIC:   like/unlike, follow/unfollow, reorder, toggle
  NEVER OPTIMISTIC: payments, send money, delete account, publish post
                    (irreversible or has server-side validation)
```

---
