# What's new in React 19 and where would you actually use it?

> **Interview priority:** GOOD TO KNOW

## Question

What's new in React 19 and where would you actually use it?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "React 19 is really about removing boilerplate from patterns that were
> already proven. The two things I'm most excited about are use() and
> Server Actions — they eliminate the awkward useEffect-for-fetching pattern
> and the need for separate API route files for simple mutations."

```
REAL APP: Todo Application — Before vs After React 19

  BEFORE React 19 — data fetching pattern:
  ──────────────────────────────────────────
  function TodoList() {
    const [todos, setTodos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
      fetch('/api/todos')
        .then(r => r.json())
        .then(data => { setTodos(data); setLoading(false); })
        .catch(err => { setError(err); setLoading(false); });
    }, []);

    if (loading) return <Spinner />;
    if (error) return <Error />;
    return <ul>{todos.map(t => <li key={t.id}>{t.text}</li>)}</ul>;
  }
  // 15 lines just to fetch data

  AFTER React 19 — use() hook:
  ─────────────────────────────
  // Create the promise OUTSIDE the component (stable reference)
  const todosPromise = fetch('/api/todos').then(r => r.json());

  function TodoList() {
    const todos = use(todosPromise);
    // use() suspends if promise is pending
    // throws to ErrorBoundary if rejected
    // returns data if resolved
    return <ul>{todos.map(t => <li key={t.id}>{t.text}</li>)}</ul>;
  }
  // Wrap in Suspense + ErrorBoundary (instead of loading/error state):
  <ErrorBoundary fallback={<Error />}>
    <Suspense fallback={<Spinner />}>
      <TodoList />
    </Suspense>
  </ErrorBoundary>
  // 3 lines in the component, loading/error handled declaratively
```

```
  SERVER ACTIONS — eliminate the API route file:
  ───────────────────────────────────────────────
  // BEFORE: Need an API route + a fetch call + error handling
  // pages/api/todos.ts:
  export default async function handler(req, res) {
    if (req.method === 'POST') {
      await db.todos.create({ text: req.body.text });
      res.json({ success: true });
    }
  }
  // Component:
  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('/api/todos', { method: 'POST', body: JSON.stringify(...) });
    router.refresh();
  };

  // AFTER React 19 Server Actions:
  // actions.ts
  'use server';
  export async function createTodo(formData: FormData) {
    const text = formData.get('text') as string;
    await db.todos.create({ text });
    revalidatePath('/todos');  // refresh the page data
  }

  // Component — no useEffect, no fetch, no API route needed:
  <form action={createTodo}>
    <input name="text" placeholder="Add todo..." />
    <SubmitButton />   {/* uses useFormStatus for pending state */}
  </form>

  // SubmitButton:
  function SubmitButton() {
    const { pending } = useFormStatus(); // knows parent form is submitting
    return <button disabled={pending}>{pending ? 'Adding...' : 'Add'}</button>;
  }
```

```
  useOptimistic — replaces verbose onMutate pattern:
  ────────────────────────────────────────────────────
  // BEFORE (React Query onMutate pattern — 20+ lines)
  // AFTER (React 19 useOptimistic — 5 lines):

  function Todos({ todos }) {
    const [optimisticTodos, addOptimisticTodo] = useOptimistic(
      todos,
      (state, newTodo) => [...state, { ...newTodo, sending: true }]
    );

    async function formAction(formData) {
      const newTodo = { text: formData.get('text'), id: Date.now() };
      addOptimisticTodo(newTodo);  // UI updates INSTANTLY
      await createTodo(formData);  // server action runs in background
      // On success: useOptimistic reverts and shows real server data
      // On failure: useOptimistic reverts to original todos
    }

    return (
      <>
        <ul>
          {optimisticTodos.map(todo => (
            <li key={todo.id} style={{ opacity: todo.sending ? 0.5 : 1 }}>
              {todo.text} {todo.sending && '(saving...)'}
            </li>
          ))}
        </ul>
        <form action={formAction}>
          <input name="text" /><button>Add</button>
        </form>
      </>
    );
  }
```

---
