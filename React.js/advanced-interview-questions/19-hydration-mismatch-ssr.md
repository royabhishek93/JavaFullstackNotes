# What causes hydration mismatch errors in SSR?

> **Interview priority:** MUST KNOW

## Question

What causes hydration mismatch errors in server-side rendering (SSR)?

## Beginner Lens

Watch the timeline: server renders HTML at build time (or request time), browser receives that HTML, React loads and tries to "hydrate" (attach event handlers to existing HTML). If the HTML React generates on the client doesn't match the server HTML, you get a hydration error. Common causes: timestamps, random values, localStorage, window object — anything that's different between server and client.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Hydration errors are one of the most confusing SSR bugs because they only show up in production or when JavaScript loads in the browser — not during development server rendering. The core issue is that React expects the client-side render to produce identical HTML to the server. When they mismatch, React can't safely attach event listeners, so it throws an error and often re-renders the whole page. Let me show the exact scenarios..."

```
REAL APP: User Dashboard with "Last Login" — Hydration Mismatch
─────────────────────────────────────────────────────────────────

BUGGY CODE (timestamp rendered differently on server vs client):
────────────────────────────────────────────────────────────────

// In Next.js or similar SSR framework
function Dashboard({ user }) {
  return (
    <div>
      <h1>Welcome back, {user.name}!</h1>
      <p>Current time: {new Date().toLocaleString()}</p>  {/* ← BUG */}
      <p>Last login: {user.lastLogin}</p>
    </div>
  );
}

THE BUG — WHAT HAPPENS:
─────────────────────────────────────────────────────────────────

STEP 1: SERVER RENDERS (at build time or request time)
────────────────────────────────────────────────────────
Time on server: 2024-01-15 10:00:00 AM EST

Server generates HTML:
<div>
  <h1>Welcome back, John!</h1>
  <p>Current time: 1/15/2024, 10:00:00 AM</p>  ← server timestamp
  <p>Last login: 1/14/2024</p>
</div>

This HTML is sent to browser and displayed immediately.
User sees page before JavaScript loads ✅


STEP 2: CLIENT HYDRATES (JavaScript loads in browser)
────────────────────────────────────────────────────────
Time on client: 2024-01-15 10:00:02 AM (2 seconds later)
OR: Different timezone: 10:00 AM PST (3 hours behind EST)

React runs the same component:
<div>
  <h1>Welcome back, John!</h1>
  <p>Current time: 1/15/2024, 10:00:02 AM</p>  ← client timestamp
  <p>Last login: 1/14/2024</p>
</div>

React compares:
  Server: "Current time: 1/15/2024, 10:00:00 AM"
  Client: "Current time: 1/15/2024, 10:00:02 AM"
  ❌ MISMATCH!

CONSOLE ERROR:
────────────────────────────────────────────────────────
Warning: Text content did not match. Server: "1/15/2024, 10:00:00 AM"
Client: "1/15/2024, 10:00:02 AM"

Warning: An error occurred during hydration. The server HTML was replaced
with client content in <div>.

RESULT: React discards server HTML and re-renders ❌
        Page flickers (FOUC - flash of unstyled content)
        Event handlers might not attach correctly
```

```
VISUAL TIMELINE — HYDRATION PROCESS:
─────────────────────────────────────────────────────────────────

Normal Hydration (no mismatch):
────────────────────────────────────────────────────────────────

t=0ms:     User requests /dashboard
           Server runs React component
           ├─ Generates HTML
           └─ Sends to browser

t=50ms:    Browser receives HTML
           └─ Displays page immediately (fast!)
              User sees content ✅

t=200ms:   JavaScript bundle loads
           React runs component again
           ├─ Generates virtual DOM
           └─ Compares to existing HTML

t=201ms:   HTML matches ✅
           ├─ React attaches event listeners to existing DOM
           ├─ No re-render needed
           └─ Page interactive ✅

Hydration complete. No flicker. Smooth ✅


Broken Hydration (timestamp mismatch):
────────────────────────────────────────────────────────────────

t=0ms:     Server renders at 10:00:00
           HTML: "Current time: 10:00:00"

t=50ms:    Browser displays HTML
           User sees: "Current time: 10:00:00" ✅

t=200ms:   JavaScript loads at 10:00:02
           React renders: "Current time: 10:00:02"
           
t=201ms:   Comparison:
           ├─ Server: "10:00:00"
           ├─ Client: "10:00:02"
           └─ ❌ MISMATCH

t=202ms:   React panics:
           ├─ Throws warning
           ├─ Discards server HTML
           └─ Re-renders from scratch

t=203ms:   User sees flash:
           "10:00:00" → (flicker) → "10:00:02"
           Event handlers re-attached
           Scroll position might reset ❌

Hydration failed. Bad UX ❌
```

```
COMMON CAUSES OF HYDRATION MISMATCH:
─────────────────────────────────────────────────────────────────

1. TIMESTAMPS (current time)
────────────────────────────────────────────────────────────────

❌ WRONG:
function Header() {
  return <div>Today is {new Date().toLocaleDateString()}</div>;
}
// Server: renders at build time (yesterday)
// Client: renders now (today)
// Mismatch ❌

✅ CORRECT (client-only rendering):
function Header() {
  const [currentDate, setCurrentDate] = useState(null);
  
  useEffect(() => {
    setCurrentDate(new Date().toLocaleDateString());
  }, []);
  
  return <div>Today is {currentDate || 'Loading...'}</div>;
}
// Server: renders "Loading..."
// Client: initially renders "Loading..." (matches!) ✅
//         Then useEffect updates to real date
//         React reconciliation handles the update ✅


2. RANDOM VALUES
────────────────────────────────────────────────────────────────

❌ WRONG:
function Banner() {
  const randomColor = ['red', 'blue', 'green'][Math.floor(Math.random() * 3)];
  return <div style={{ background: randomColor }}>Welcome!</div>;
}
// Server: picks "blue"
// Client: picks "green"
// Mismatch ❌

✅ CORRECT (stable random via prop):
// Generate random value ONCE on server, pass as prop
export async function getServerSideProps() {
  const randomColor = ['red', 'blue', 'green'][Math.floor(Math.random() * 3)];
  return { props: { bannerColor: randomColor } };
}

function Banner({ bannerColor }) {
  return <div style={{ background: bannerColor }}>Welcome!</div>;
}
// Server: renders with prop "blue"
// Client: renders with same prop "blue"
// Match ✅


3. LOCALSTORAGE / COOKIES (browser-only APIs)
────────────────────────────────────────────────────────────────

❌ WRONG:
function UserGreeting() {
  const username = localStorage.getItem('username') || 'Guest';
  return <div>Hello, {username}!</div>;
}
// Server: localStorage doesn't exist → crash or "Guest"
// Client: localStorage exists → "John"
// Mismatch ❌

✅ CORRECT (two-pass render):
function UserGreeting() {
  const [username, setUsername] = useState('Guest');
  
  useEffect(() => {
    const stored = localStorage.getItem('username');
    if (stored) setUsername(stored);
  }, []);
  
  return <div>Hello, {username}!</div>;
}
// Server: renders "Guest"
// Client: initially renders "Guest" (matches!) ✅
//         Then useEffect reads localStorage and updates
// OR: Use suppressHydrationWarning for known mismatches


4. WINDOW OBJECT (browser-only)
────────────────────────────────────────────────────────────────

❌ WRONG:
function Viewport() {
  const width = window.innerWidth;  // ← crashes on server
  return <div>Width: {width}px</div>;
}

✅ CORRECT:
function Viewport() {
  const [width, setWidth] = useState(0);
  
  useEffect(() => {
    setWidth(window.innerWidth);
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  return <div>Width: {width > 0 ? `${width}px` : 'Calculating...'}</div>;
}


5. USER-AGENT DETECTION (different on server vs client)
────────────────────────────────────────────────────────────────

❌ WRONG:
function MobileNotice() {
  const isMobile = /mobile/i.test(navigator.userAgent);
  return isMobile ? <div>Mobile view</div> : <div>Desktop view</div>;
}
// Server: gets request User-Agent → "Mobile view"
// Client: navigator.userAgent might differ → "Desktop view"
// Mismatch ❌

✅ CORRECT (CSS media queries or client-only detection):
function MobileNotice() {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    setIsMobile(window.matchMedia('(max-width: 768px)').matches);
  }, []);
  
  return isMobile ? <div>Mobile view</div> : <div>Desktop view</div>;
}
```

```
THE suppressHydrationWarning ESCAPE HATCH:
─────────────────────────────────────────────────────────────────

// Use ONLY when you KNOW the mismatch is intentional and safe

function Timestamp() {
  return (
    <time suppressHydrationWarning>
      {new Date().toLocaleString()}
    </time>
  );
}

What it does:
  - Tells React "I know this won't match, don't warn me"
  - React still REPLACES the server HTML with client HTML
  - No console error, but still causes re-render

When to use:
  ✅ Timestamps, date displays
  ✅ "You are visitor #12345" (changes every request)
  ✅ A/B test variants (intentionally different)

When NOT to use:
  ❌ To silence errors you don't understand
  ❌ For large components (causes expensive re-render)
  ❌ When you can fix it with useEffect pattern instead
```

```
BEST PATTERN: TWO-PASS RENDER
─────────────────────────────────────────────────────────────────

1. First render (server + client initial): safe default value
2. Second render (client only, after mount): real value

function DynamicContent() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);  // component is now on client
  }, []);
  
  if (!mounted) {
    // Server renders this
    // Client ALSO renders this on initial mount
    return <div>Loading...</div>;  // ← matches perfectly ✅
  }
  
  // Client renders this AFTER hydration
  return (
    <div>
      <p>Time: {new Date().toLocaleString()}</p>
      <p>Width: {window.innerWidth}px</p>
      <p>User: {localStorage.getItem('name')}</p>
    </div>
  );
}

Timeline:
  t=0:   Server renders "Loading..." → sends HTML
  t=50:  Browser displays "Loading..."
  t=200: JavaScript loads, React hydrates
         mounted = false → renders "Loading..." ✅ Match!
  t=201: useEffect runs → setMounted(true)
  t=202: Re-render with real dynamic content
         (uses normal React update, no hydration error)
```

```
NEXT.JS SPECIFIC SOLUTIONS:
─────────────────────────────────────────────────────────────────

1. USE DYNAMIC IMPORT with ssr: false
────────────────────────────────────────────────────────────────

import dynamic from 'next/dynamic';

const ClientOnlyComponent = dynamic(
  () => import('../components/ClientOnly'),
  { ssr: false }  // ← don't render on server at all
);

function Page() {
  return (
    <div>
      <h1>Welcome</h1>
      <ClientOnlyComponent />  {/* only runs in browser */}
    </div>
  );
}


2. USE getServerSideProps FOR DYNAMIC DATA
────────────────────────────────────────────────────────────────

// Generate value ONCE on server, pass to component

export async function getServerSideProps(context) {
  const currentTime = new Date().toISOString();
  const userAgent = context.req.headers['user-agent'];
  
  return {
    props: { currentTime, userAgent }
  };
}

function Page({ currentTime, userAgent }) {
  return <div>Rendered at {currentTime}</div>;
  // Server and client both use the SAME currentTime value ✅
}
```

```
DEBUGGING CHECKLIST — "Hydration error in production"
─────────────────────────────────────────────────────────────────

✅ Check for Date() or Date.now() in render
   → Move to useEffect or getServerSideProps

✅ Check for Math.random() in render
   → Generate once on server, pass as prop

✅ Check for window, localStorage, navigator
   → Guard with typeof window !== 'undefined'
   → Or use two-pass render pattern

✅ Check for user-specific data without props
   → Fetch in getServerSideProps
   → Or render loading state first

✅ Check third-party libraries
   → Some components aren't SSR-compatible
   → Use dynamic import with ssr: false

✅ Look at the error message closely
   Server: "X"
   Client: "Y"
   → What's different? Why?

✅ Reproduce in dev mode
   → Next.js dev mode shows hydration errors clearly
   → Production might just flash without error details
```

```
PRODUCTION BUG EXAMPLE — A/B TEST FLICKER:
─────────────────────────────────────────────────────────────────

// Old buggy code:
function Hero() {
  const variant = Math.random() > 0.5 ? 'A' : 'B';
  return <h1>Version {variant}</h1>;
}

User experience:
  1. Server renders "Version A"
  2. User sees "Version A" for 200ms
  3. JavaScript loads
  4. Client renders "Version B" (random picked different value)
  5. Flash from A to B ❌
  6. User confused, metrics broken

Fixed code:
export async function getServerSideProps() {
  const variant = Math.random() > 0.5 ? 'A' : 'B';
  return { props: { variant } };
}

function Hero({ variant }) {
  return <h1>Version {variant}</h1>;
}

Now: Server picks once, client uses same value ✅
```

> "The mental model: hydration is React's way of saying 'I'm going to assume the server HTML is correct and just attach my JavaScript to it.' If the HTML doesn't match what React would generate, that assumption breaks. So anything non-deterministic (time, random, browser APIs) must be either computed on the server and passed down, or deferred to a client-only effect after hydration."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What's the performance impact of hydration mismatches?"**

> "Bad. When React detects a mismatch, it discards the server HTML and re-renders from scratch. That negates the whole point of SSR — user saw content immediately, then it flashes and re-renders. Plus, event listeners might not attach correctly, breaking interactivity."

**Q: "Can you suppress all hydration warnings globally?"**

> "Technically yes, but don't. Each warning indicates a real bug that causes FOUC or broken interactions. Fix the root cause. Use suppressHydrationWarning only on specific elements where you've consciously decided the mismatch is acceptable."

**Q: "What about time-sensitive content like stock prices?"**

> "Fetch on the server (getServerSideProps), pass as props. Both server and client render the same value. Then use useEffect with setInterval to update after hydration. The initial render matches, updates happen via normal React flow."
