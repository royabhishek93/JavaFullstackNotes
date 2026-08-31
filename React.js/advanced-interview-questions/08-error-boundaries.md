# How do Error Boundaries work? What are their limitations?

> **Interview priority:** SHOULD KNOW

## Question

How do Error Boundaries work? What are their limitations?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "Error Boundaries are React's try-catch for the render phase. Without them,
> one broken component crashes your entire app. With them, you can contain
> the damage to a specific section. Let me show how I'd structure them for
> a news feed app like Twitter..."

```
REAL APP: Twitter/X-style Feed

  WITHOUT ERROR BOUNDARIES:
  ──────────────────────────────────────────────────────────────
  User opens feed → Tweet #247 has malformed data (null author)
  Tweet component throws: "Cannot read properties of null (reading 'name')"
  ENTIRE FEED crashes → blank white screen → user sees nothing

  WITH GRANULAR ERROR BOUNDARIES:
  ──────────────────────────────────────────────────────────────
  <App>
    <ErrorBoundary fallback={<AppCrashPage />}>        ← catch-all
      <Router>
        <Route path="/feed">
          <ErrorBoundary fallback={<FeedError />}>     ← route level
            <Feed>
              {tweets.map(tweet => (
                <ErrorBoundary                         ← item level
                  key={tweet.id}
                  fallback={<BrokenTweetPlaceholder />}
                  onError={(e) => Sentry.captureException(e)}
                >
                  <Tweet data={tweet} />
                </ErrorBoundary>
              ))}
            </Feed>
          </ErrorBoundary>
        </Route>
      </Router>
    </ErrorBoundary>
  </App>

  Tweet #247 crashes → only that tweet shows placeholder
  Other 50 tweets still render ✅
  User can still scroll, like, retweet ✅
  Sentry captures the error for the engineering team ✅
```

```
IMPLEMENTATION:

  class ErrorBoundary extends React.Component {
    state = { hasError: false };

    static getDerivedStateFromError(error) {
      // Called during render phase — update state to show fallback
      return { hasError: true };
    }

    componentDidCatch(error, info) {
      // Called after render — good for logging
      // info.componentStack = which component tree threw
      Sentry.captureException(error, {
        extra: { componentStack: info.componentStack }
      });
    }

    render() {
      if (this.state.hasError) {
        return this.props.fallback;
      }
      return this.props.children;
    }
  }

  WHAT THEY CATCH:       WHAT THEY DON'T CATCH:
  ──────────────────     ───────────────────────────────────
  Errors in render()     Event handlers (use try/catch)
  Errors in lifecycle    Async errors (setTimeout, Promise)
  Errors in children     SSR errors
                         Errors in the boundary itself

  // WORKAROUND: Push async errors into render phase
  function AsyncComponent() {
    const [asyncError, setAsyncError] = useState(null);
    if (asyncError) throw asyncError; // ← caught by nearest boundary

    useEffect(() => {
      fetchData()
        .catch(err => setAsyncError(err)); // ← pushes to render phase
    }, []);
  }
```

---
