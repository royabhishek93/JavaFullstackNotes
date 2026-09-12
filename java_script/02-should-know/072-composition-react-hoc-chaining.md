# React HOC Chaining Order
> **Topic:** Composition | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A Netflix-like frontend has components that need authentication guarding, theme injection, and analytics tracking. The team is debating whether to nest HOCs manually or use `compose`.

## The Question
Walk through HOC composition using `compose`, explain the execution order, and say when you would migrate this to hooks.

## Diagram

```
HOC composition pipeline:

  Manual (unreadable at 4+ HOCs):
  withAuth(withTheme(withAnalytics(withErrorBoundary(Dashboard))))

  With compose (right-to-left):
  compose(withAuth, withTheme, withAnalytics, withErrorBoundary)(Dashboard)

  Execution order — each HOC wraps the result of the one to its right:
  Dashboard
      |
      v
  withErrorBoundary(Dashboard)       <-- innermost wrap
      |
      v
  withAnalytics(ErrorBoundaryDashboard)
      |
      v
  withTheme(AnalyticsDashboard)
      |
      v
  withAuth(ThemedDashboard)          <-- outermost wrap, renders first
      |
      v
  EnhancedDashboard (what you export)

  Render order (opposite — outermost runs first):
  withAuth checks login -> withTheme injects theme -> withAnalytics tracks -> withErrorBoundary catches -> Dashboard renders
```

## Model Answer (15 YOE)

```js
const compose = (...fns) => x => fns.reduceRight((acc, fn) => fn(acc), x);

const withAuth = Comp => props =>
  isAuthenticated() ? <Comp {...props} /> : <Navigate to="/login" />;

const withTheme = Comp => props => {
  const theme = useContext(ThemeContext);
  return <Comp {...props} theme={theme} />;
};

const withAnalytics = Comp => {
  const Wrapped = props => { useEffect(() => trackView(Comp.displayName), []); return <Comp {...props} />; };
  Wrapped.displayName = `WithAnalytics(${Comp.displayName})`;
  return Wrapped;
};

export const EnhancedDashboard = compose(withAuth, withTheme, withAnalytics)(Dashboard);
```

The `compose` call produces a single HOC. The key detail engineers miss: the HOC listed first in `compose` is the outermost wrapper at render time, so `withAuth` is the first thing that runs. If authentication fails, the inner HOCs never execute — that is the correct short-circuit behavior.

When to migrate: once the team is on React 16.8+, hooks eliminate most HOC use cases. `useAuth`, `useTheme`, `useAnalytics` inside the component are easier to test, have no prop-drilling overhead, and produce no wrapper component hell in DevTools. Keep HOCs only for cross-cutting concerns that genuinely need to wrap a component (error boundaries, code splitting).

## Follow-up

**Q:** What is the "wrapper hell" problem with deep HOC composition?

**A:** Each HOC adds a component to the React tree. Five HOCs means five extra nodes in DevTools — every debug session requires unwrapping layers to find the real component. Hooks keep the tree flat. For legacy HOC chains, add meaningful `displayName` to each wrapper so DevTools shows `WithAuth(WithTheme(Dashboard))` instead of `Component(Component(Component))`.
