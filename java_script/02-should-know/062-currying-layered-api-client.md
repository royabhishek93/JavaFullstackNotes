# API Client with Layered Configuration
> **Topic:** Currying | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are designing a shared API client library at Uber used across the Rider, Driver, and Fleet management apps. Each app shares the same base URL and authentication mechanism but calls different endpoints with different query parameters. The library is consumed both in React components and in Node.js BFF services, and it must compose cleanly with both synchronous config and async token refresh.

## The Question
Design the API client using currying to separate configuration concerns into distinct layers. Show how partial application enables reuse across apps.

## Diagram
```
  THREE CONFIGURATION LAYERS (applied at different times):

  Layer 1: App-level (at startup)
  ┌──────────────────────────────────────────┐
  │  const uberApi = apiClient               │
  │    ('https://api.uber.com/v2')           │
  │  ← baseUrl locked in for all of Rider app│
  └──────────────────────────────────────────┘
                    │
                    ▼
  Layer 2: Request-level (per authenticated session)
  ┌──────────────────────────────────────────┐
  │  const authedApi = uberApi(authToken)    │
  │  ← token locked in for this session      │
  └──────────────────────────────────────────┘
                    │
                    ▼
  Layer 3: Call-level (per feature)
  ┌──────────────────────────────────────────┐
  │  authedApi('/rides')({ limit: 10 })      │
  │  authedApi('/drivers')({ city: 'NYC' })  │
  │  ← endpoint + params supplied at use site│
  └──────────────────────────────────────────┘
```

## Model Answer (15 YOE)
The three-layer curried design maps perfectly onto the three timelines at which configuration becomes available. The base URL is known at module load time. The auth token is known after login. The endpoint and parameters are known at call sites scattered across the feature code. Forcing all three into a single function call would mean passing the base URL and token to every call site — massive repetition and a maintenance burden when the base URL changes or the token refreshes.

```js
const apiClient = (baseUrl) => (token) => (endpoint) => (params = {}) =>
  fetch(`${baseUrl}${endpoint}`, {
    method: params.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: params.body ? JSON.stringify(params.body) : undefined,
  });

// At app startup
const uberApi = apiClient('https://api.uber.com/v2');

// After login
const authedApi = uberApi(session.token);

// In feature components
const getRides  = authedApi('/rides');
const getDriver = authedApi('/drivers');

getRides({ method: 'GET' });
getDriver({ method: 'GET', body: { city: 'NYC' } });
```

The architectural benefit I emphasize: when the auth token refreshes (common in long-lived SPAs), you only need to rebuild `authedApi = uberApi(newToken)` and propagate it. All downstream feature functions that hold references to `authedApi` get the updated token on the next call — provided they call `authedApi` fresh rather than holding onto a pre-built `getDriver`. This is a subtle coupling concern worth designing explicitly.

One production consideration: this pattern assumes the token does not change mid-call. For OAuth token refresh flows, I use a factory that reads the token lazily from a shared token store rather than closing over a specific token value.

## Follow-up
**Q:** How would you handle the token refresh case without breaking the curried API?

**A:** Instead of closing over a token value, close over a token provider — a function that returns the current token: `(getToken) => (endpoint) => (params) => fetch(..., { headers: { Authorization: \`Bearer ${getToken()}\` } })`. The token is read at request time, not at configuration time. The curried structure is preserved; the token resolution is deferred.
