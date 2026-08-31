# How do you choose your state management approach?

> **Interview priority:** MUST KNOW

## Question

How do you choose your state management approach?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "The mistake I've seen teams make — including ones I've been on — is
> treating all state the same. In a Slack-style chat app, for example,
> you have at least 4 completely different categories of state. Getting
> this categorization right first saves you from over-engineering."

```
REAL APP: Slack-style Chat Application

  STATE CATEGORY MAP:
  ──────────────────────────────────────────────────────────────
  Category         Example                    Best Tool
  ───────────────  ─────────────────────────  ──────────────────
  Server state     Message list, user list,   React Query
                   channel info               (cache, polling,
                                              background refetch)

  Global UI state  Current user, theme,       Zustand (simple)
                   sidebar open/closed,       or Context (small)
                   notification count

  URL state        Active channel, search     URL search params
                   query, selected message    (survives refresh,
                                              shareable link)

  Local state      Is this message being      useState in that
                   edited? Input value        component only

  Form state       Create channel form,       React Hook Form
                   edit profile form          (uncontrolled,
                                              fast, validation)
  ──────────────────────────────────────────────────────────────

  WHAT PUTTING EVERYTHING IN REDUX LOOKS LIKE (anti-pattern):
  store = {
    messages: [...],          // should be React Query
    users: [...],             // should be React Query
    channels: [...],          // should be React Query
    currentUser: {...},       // OK in Zustand/Context
    theme: 'dark',            // OK in Context
    searchQuery: 'react',     // should be URL param
    messageInputValue: '...'  // should be local useState
  }
  // Result: Redux store changes 50x/sec from typing
  // Devtools become useless noise
  // Everything re-renders on every keypress
```

```
CONTEXT RE-RENDER TRAP — THE HIDDEN PERFORMANCE KILLER:

  // BAD: One context with many concerns
  const AppContext = createContext({
    user,           // changes on login/logout
    theme,          // changes on toggle
    notifications,  // changes every few seconds
    activeChannel   // changes on every channel click
  });

  Component tree with BAD context:
  ┌─────────────────────────────────────────────────────────┐
  │  AppContext.Provider (value = { user, theme, notifs })   │
  │        │                                                 │
  │   ┌────┼────────────────────────┐                        │
  │   │    │                        │                        │
  │  UserAvatar  ThemeToggle   NotifBadge                    │
  │  (needs      (needs         (needs                        │
  │   user)       theme)         notifs)                      │
  └─────────────────────────────────────────────────────────┘

  New notification arrives → value object is NEW reference
  → UserAvatar re-renders  ← WRONG, user didn't change
  → ThemeToggle re-renders ← WRONG, theme didn't change
  → NotifBadge re-renders  ← correct

  // FIX: Split by update frequency
  const UserContext  = createContext(user);         // rare updates
  const ThemeContext = createContext(theme);        // rare updates
  const NotifContext = createContext(notifications);// frequent

  New notification → only NotifBadge re-renders ✅

  // ALSO: Stabilize the value object itself
  const value = useMemo(
    () => ({ user, updateUser }),
    [user]  // only new object when user actually changes
  );
```

> "The test I apply: if I remove React Query and replace it with a plain
> useEffect + useState combo, does my code get significantly more complex?
> Yes every time — because you'd be rebuilding cache invalidation, background
> refetch, loading/error states, and deduplication from scratch."

---
