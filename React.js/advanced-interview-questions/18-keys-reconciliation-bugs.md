# Why does using array index as a key cause bugs?

> **Interview priority:** MUST KNOW

## Question

Why does using array index as a key cause bugs in React lists?

## Beginner Lens

Watch what React does when an item is deleted: it uses keys to match old elements to new elements. When you use array indices as keys, deleting item 0 makes item 1 become the new item 0, so React thinks item 0 changed its content instead of being deleted. This causes state and input values to appear under the wrong items.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "This is one of those bugs that's invisible in simple demos but breaks real forms in production. The core issue is that keys tell React which DOM element corresponds to which component instance. When you use the array index, you're saying 'this is the Nth item' — but if items can be added, removed, or reordered, the Nth position doesn't identify a stable item. Let me show exactly what goes wrong..."

```
REAL APP: Todo List — The Classic Key Bug
─────────────────────────────────────────────────────────────────

SCENARIO: User has 3 todos, each with a checkbox. User deletes the first one.

BUGGY CODE (using index as key):
────────────────────────────────────────────────────────────────

function TodoList() {
  const [todos, setTodos] = useState([
    { id: 'a1', text: 'Buy milk', done: false },
    { id: 'b2', text: 'Call mom', done: true },
    { id: 'c3', text: 'Fix bug', done: false }
  ]);

  const deleteTodo = (index) => {
    setTodos(todos.filter((_, i) => i !== index));
  };

  return (
    <ul>
      {todos.map((todo, index) => (
        <TodoItem
          key={index}  // ← BUG: using index as key
          todo={todo}
          onDelete={() => deleteTodo(index)}
        />
      ))}
    </ul>
  );
}

function TodoItem({ todo, onDelete }) {
  const [isEditing, setIsEditing] = useState(false);
  
  return (
    <li>
      <input type="checkbox" checked={todo.done} />
      <span>{todo.text}</span>
      <button onClick={onDelete}>Delete</button>
      {isEditing && <input type="text" defaultValue={todo.text} />}
    </li>
  );
}

THE BUG — WHAT ACTUALLY HAPPENS:
─────────────────────────────────────────────────────────────────

BEFORE DELETE: User sees 3 todos
┌─────────────────────────────────────────────────────────────┐
│ [ ] Buy milk    [Delete]     ← key=0, checkbox unchecked    │
│ [✓] Call mom    [Delete]     ← key=1, checkbox checked      │
│ [ ] Fix bug     [Delete]     ← key=2, checkbox unchecked    │
└─────────────────────────────────────────────────────────────┘

User clicks Delete on "Buy milk" (index 0)

AFTER DELETE: todos array becomes:
  [
    { id: 'b2', text: 'Call mom', done: true },   ← now at index 0
    { id: 'c3', text: 'Fix bug', done: false }    ← now at index 1
  ]

REACT'S RECONCILIATION (what React thinks):
────────────────────────────────────────────────────────────────

OLD VDOM:                    NEW VDOM:
─────────────────────────    ─────────────────────────
<li key=0>                   <li key=0>
  Buy milk                     Call mom          ← CHANGED
  checkbox: unchecked          checkbox: checked ← CHANGED
</li>                        </li>

<li key=1>                   <li key=1>
  Call mom                     Fix bug           ← CHANGED
  checkbox: checked            checkbox: unchecked ← CHANGED
</li>                        </li>

<li key=2>                   (deleted)
  Fix bug
  checkbox: unchecked
</li>

React sees:
  - key=0 UPDATED (text changed, checkbox changed)
  - key=1 UPDATED (text changed, checkbox changed)
  - key=2 DELETED

RESULT ON SCREEN:
┌─────────────────────────────────────────────────────────────┐
│ [ ] Call mom    [Delete]     ← WRONG! checkbox lost state   │
│ [✓] Fix bug     [Delete]     ← WRONG! checkbox has wrong state│
└─────────────────────────────────────────────────────────────┘

WHY IT'S WRONG:
  - "Call mom" shows unchecked (was checked before) ❌
  - "Fix bug" shows checked (was unchecked before) ❌
  - Checkbox state was RECYCLED from old positions

React reused the DOM elements:
  - The DOM <input> from old key=1 got new text "Fix bug"
  - The checkbox stayed checked (from "Call mom")
  - React thought it was just updating text, not swapping items
```

```
VISUAL DIAGRAM — WHY INDEX KEYS FAIL:
─────────────────────────────────────────────────────────────────

BEFORE:
  Index   Key    Todo         DOM Element (with state)
  ─────   ───    ──────────   ────────────────────────
    0      0     Buy milk     <li> with unchecked checkbox
    1      1     Call mom     <li> with checked checkbox
    2      2     Fix bug      <li> with unchecked checkbox

User deletes index 0 → todos array shifts:

AFTER:
  Index   Key    Todo         React's matching logic
  ─────   ───    ──────────   ────────────────────────────────
    0      0     Call mom  ← key=0 REUSED, text updated
    1      1     Fix bug   ← key=1 REUSED, text updated
    -      2     (deleted) ← key=2 DELETED

React matched by key:
  Old key=0 → New key=0: UPDATE text to "Call mom"
              BUT: reuses old DOM (unchecked checkbox) ❌
  Old key=1 → New key=1: UPDATE text to "Fix bug"
              BUT: reuses old DOM (checked checkbox) ❌
  Old key=2 → Not in new list: DELETE

The problem: Keys don't identify ITEMS, they identify POSITIONS.
```

```
CORRECT CODE (using stable unique IDs as keys):
────────────────────────────────────────────────────────────────

function TodoList() {
  const [todos, setTodos] = useState([
    { id: 'a1', text: 'Buy milk', done: false },
    { id: 'b2', text: 'Call mom', done: true },
    { id: 'c3', text: 'Fix bug', done: false }
  ]);

  const deleteTodo = (id) => {
    setTodos(todos.filter(todo => todo.id !== id));
  };

  return (
    <ul>
      {todos.map((todo) => (
        <TodoItem
          key={todo.id}  // ✅ CORRECT: stable unique ID
          todo={todo}
          onDelete={() => deleteTodo(todo.id)}
        />
      ))}
    </ul>
  );
}

REACT'S RECONCILIATION (with correct keys):
────────────────────────────────────────────────────────────────

OLD VDOM:                    NEW VDOM:
─────────────────────────    ─────────────────────────
<li key="a1">                (deleted) ← key="a1" gone
  Buy milk
  checkbox: unchecked
</li>

<li key="b2">                <li key="b2">
  Call mom                     Call mom          ← NO CHANGE
  checkbox: checked            checkbox: checked  ← PRESERVED
</li>                        </li>

<li key="c3">                <li key="c3">
  Fix bug                      Fix bug           ← NO CHANGE
  checkbox: unchecked          checkbox: unchecked ← PRESERVED
</li>                        </li>

React sees:
  - key="a1" DELETED (remove that DOM element)
  - key="b2" NO CHANGE (keep DOM element, no update)
  - key="c3" NO CHANGE (keep DOM element, no update)

RESULT ON SCREEN:
┌─────────────────────────────────────────────────────────────┐
│ [✓] Call mom    [Delete]     ← CORRECT! checkbox preserved  │
│ [ ] Fix bug     [Delete]     ← CORRECT! checkbox preserved  │
└─────────────────────────────────────────────────────────────┘

React matched by ID:
  - Old "a1" → Not in new list: DELETE the entire <li> DOM element
  - Old "b2" → New "b2": KEEP (no props changed, no re-render)
  - Old "c3" → New "c3": KEEP (no props changed, no re-render)

The checkbox state stayed with the correct todo item ✅
```

```
MORE REAL BUGS — WHEN INDEX KEYS BREAK:
─────────────────────────────────────────────────────────────────

1. FORM INPUTS SWAP VALUES
────────────────────────────────────────────────────────────────

// Multi-step form with deletable fields
function FieldList() {
  const [fields, setFields] = useState([
    { id: 1, name: 'John' },
    { id: 2, name: 'Jane' },
    { id: 3, name: 'Bob' }
  ]);

  return fields.map((field, index) => (
    <input
      key={index}  // ← BUG
      defaultValue={field.name}
    />
  ));
}

User deletes "John" (index 0):
  - React reuses DOM <input> that had "John"
  - Updates defaultValue to "Jane"
  - BUT: <input> value is UNCONTROLLED
  - User sees "John" still in the input ❌ (DOM not updated)


2. ANIMATIONS GLITCH
────────────────────────────────────────────────────────────────

function AnimatedList({ items }) {
  return items.map((item, index) => (
    <motion.div
      key={index}  // ← BUG
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {item.text}
    </motion.div>
  ));
}

User deletes first item:
  - React reuses animated <div> components
  - Animation doesn't replay for "new" items
  - Items slide into wrong positions ❌


3. FOCUS LOST ON REORDER
────────────────────────────────────────────────────────────────

function TodoList({ todos }) {
  return todos.map((todo, index) => (
    <input
      key={index}  // ← BUG
      value={todo.text}
      autoFocus={index === 0}
    />
  ));
}

User reorders (move item 2 to position 0):
  - React updates text in existing DOM inputs
  - autoFocus tries to focus index 0
  - But index 0 DOM element is REUSED, not remounted
  - autoFocus doesn't fire ❌
```

```
WHEN CAN YOU USE INDEX AS KEY?
─────────────────────────────────────────────────────────────────

✅ Safe to use index as key when:

1. List is STATIC (never changes)
   const items = ['Red', 'Green', 'Blue'];
   items.map((color, i) => <div key={i}>{color}</div>);
   // OK — colors never added/removed/reordered

2. List is APPEND-ONLY (items only added to end)
   const logs = [...oldLogs, newLog];
   logs.map((log, i) => <div key={i}>{log}</div>);
   // OK — old indices stay stable

3. Items have NO internal state
   items.map((name, i) => <div key={i}>{name}</div>);
   // OK — pure display, no checkboxes/inputs/animations

❌ NEVER use index as key when:
  - Items can be deleted
  - Items can be reordered (drag-and-drop, sort)
  - Items have checkboxes, inputs, or local state
  - Items can be filtered
  - Items are animated
```

```
GENERATING UNIQUE KEYS — BEST PRACTICES:
─────────────────────────────────────────────────────────────────

1. USE DATABASE ID (best)
   todos.map(todo => <TodoItem key={todo.id} ... />)
   // Server provides unique ID

2. USE UUID (good for client-side creation)
   import { v4 as uuidv4 } from 'uuid';
   const newTodo = { id: uuidv4(), text: 'New task' };

3. USE STABLE HASH (for composite data)
   const key = `${user.id}-${date}-${type}`;

4. USE INDEX + ID COMBO (for nested lists)
   categories.map((cat, catIndex) =>
     cat.items.map(item => 
       <Item key={`${catIndex}-${item.id}`} />
     )
   )

❌ NEVER:
  - Math.random() as key (generates new key every render → destroys DOM)
  - Date.now() as key (same problem)
  - toString() of object (same object = same string = collision)
```

```
DEBUGGING CHECKLIST — "My list items swap data"
─────────────────────────────────────────────────────────────────

✅ Are you using index as key?
   {items.map((item, i) => <div key={i}>...)}
   → YES? Replace with item.id

✅ Do items have checkboxes, inputs, or useState?
   → YES? You MUST use stable IDs as keys

✅ Can users delete, reorder, or filter items?
   → YES? Index keys will break

✅ Do you see React warning "Each child should have unique key"?
   → Missing or duplicate keys — add/fix them

✅ Open React DevTools → check key values
   → Are they stable when list changes?

✅ Does the bug only happen after delete/reorder?
   → Classic symptom of index key bug
```

> "The mental model: keys are React's way of matching old DOM to new data. An index is a position, not an identity. When positions shift (delete/reorder), indices point to different items, so React matches the wrong DOM element to the wrong data. Use IDs that follow the item, not its position."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What if I don't have unique IDs in my data?"**

> "Generate them when data enters your app. If fetching from API, add IDs in the transform step. If user creates items, assign UUIDs immediately. Never rely on indices for anything that can change."

**Q: "Does using the same key for different items cause issues?"**

> "Yes — duplicate keys confuse React's reconciliation. React Dev Tools will warn you. Each key must be unique among siblings. Using `${parentId}-${childId}` helps in nested lists."

**Q: "What's the performance impact of bad keys?"**

> "Terrible. Index keys cause unnecessary DOM updates. React thinks items changed when they didn't. With stable IDs, deleting item 1 of 1000 = 1 DOM operation. With index keys = 999 DOM updates (every item after it). That's why lists get slow."
