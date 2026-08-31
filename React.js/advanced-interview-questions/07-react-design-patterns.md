# Compare Compound Components vs Render Props vs HOC.

> **Interview priority:** SHOULD KNOW

## Question

Compare Compound Components vs Render Props vs HOC.

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "These are three solutions to the same problem: how do you build flexible,
> reusable components without prop explosion? Let me show each one using a
> real design system example — a Select dropdown."

```
REAL APP: Design System — Select Dropdown Component

  PATTERN 1: COMPOUND COMPONENTS (2023+ preferred)
  ──────────────────────────────────────────────────
  // What the consumer writes:
  <Select defaultValue="mumbai" onChange={handleChange}>
    <Select.Trigger placeholder="Choose city" />
    <Select.Dropdown>
      <Select.Group label="Maharashtra">
        <Select.Option value="mumbai">Mumbai</Select.Option>
        <Select.Option value="pune">Pune</Select.Option>
      </Select.Group>
      <Select.Group label="Karnataka">
        <Select.Option value="bangalore">Bangalore</Select.Option>
      </Select.Group>
    </Select.Dropdown>
  </Select>

  // HOW IT WORKS INTERNALLY:
  // Select creates Context:
  const SelectContext = createContext(null);
  
  function Select({ defaultValue, onChange, children }) {
    const [selected, setSelected] = useState(defaultValue);
    const [isOpen, setIsOpen] = useState(false);
    
    const value = useMemo(() => ({
      selected, setSelected, isOpen, setIsOpen, onChange
    }), [selected, isOpen]);
    
    return (
      <SelectContext.Provider value={value}>
        <div className="select-wrapper">{children}</div>
      </SelectContext.Provider>
    );
  }
  
  // Select.Option reads from context — no prop drilling:
  Select.Option = function({ value, children }) {
    const { selected, setSelected, onChange } = useContext(SelectContext);
    return (
      <li
        className={selected === value ? 'active' : ''}
        onClick={() => { setSelected(value); onChange(value); }}
      >
        {children}
      </li>
    );
  };

  WHY THIS IS BEST:
  ✓ Consumer controls the structure (can add icons, groups, search)
  ✓ No prop drilling (40+ props on a single <Select> tag)
  ✓ Each sub-component is independently testable
  ✓ Matches how HTML native elements work (<table>, <tr>, <td>)
```

```
  PATTERN 2: RENDER PROPS (still valid for lists/tables)
  ──────────────────────────────────────────────────────
  // When the LIBRARY controls structure but YOU control content
  // Example: react-window, tanstack-table

  <FixedSizeList
    height={600}
    itemCount={transactions.length}
    itemSize={50}
    width="100%"
  >
    {({ index, style }) => (          // render prop
      <div style={style}>
        <TransactionRow data={transactions[index]} />
      </div>
    )}
  </FixedSizeList>

  // Library owns: virtualization, scroll, measurement
  // You own: what each row looks like

  STILL VALID IN 2024 FOR:
  ✓ react-window / react-virtual (renderItem)
  ✓ tanstack-table (cell renderers)
  ✓ When structure varies so much that a hook can't capture it

  REPLACED BY CUSTOM HOOKS FOR:
  ✗ Data fetching logic (useFetch is cleaner than DataFetcher render prop)
  ✗ Mouse/keyboard tracking (useMousePosition)
  ✗ Form state (React Hook Form)
```

```
  PATTERN 3: HOC — Higher Order Component
  ──────────────────────────────────────────
  // Takes a component, returns enhanced component
  // Best for: cross-cutting concerns at routing level

  // Auth guard HOC:
  function withAuth(Component) {
    return function AuthenticatedComponent(props) {
      const { user, isLoading } = useAuth();
      if (isLoading) return <PageLoader />;
      if (!user) return <Navigate to="/login" />;
      return <Component {...props} user={user} />;
    };
  }

  const ProtectedDashboard = withAuth(Dashboard);
  const ProtectedProfile   = withAuth(Profile);
  const ProtectedSettings  = withAuth(Settings);

  // Analytics HOC:
  function withPageTracking(Component, pageName) {
    return function TrackedPage(props) {
      useEffect(() => {
        analytics.track('page_view', { page: pageName });
      }, []);
      return <Component {...props} />;
    };
  }

  WHEN HOC IS RIGHT:
  ✓ Wrapping at the route/page level (auth, tracking, error boundaries)
  ✓ Behavior that wraps the entire component (not part of its render)

  WHEN TO PREFER CUSTOM HOOK:
  ✗ Logic that a component needs internally (use useAuth() directly)
  ✗ When prop collisions are likely (HOC injects 'user' — what if Component
    already has a 'user' prop? Collision.)

  HOC PROP COLLISION PROBLEM:
  const Wrapped = withUser(withData(withTheme(MyComponent)));
  // If all three inject a prop called 'data' — last one wins silently
  // Custom hooks don't have this problem
```

---
