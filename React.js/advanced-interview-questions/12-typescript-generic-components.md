# How do you type a generic reusable component in TypeScript?

> **Interview priority:** GOOD TO KNOW

## Question

How do you type a generic reusable component in TypeScript?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "The most powerful TypeScript pattern I use in React is the generic component.
> It lets type information flow through the component without you having to
> specify it at every call site. I'll show with a real example — a reusable
> table component that works for users, orders, products, anything."

```
REAL APP: Reusable Data Table (works for any entity type)

  // WITHOUT GENERICS — you'd need separate tables:
  function UserTable({ users }: { users: User[] }) { ... }
  function OrderTable({ orders }: { orders: Order[] }) { ... }
  function ProductTable({ products }: { products: Product[] }) { ... }
  // 3x code duplication

  // WITH GENERICS — one table, TypeScript enforces correctness:
  interface Column<T> {
    header: string;
    accessor: keyof T;                    // must be a key of T
    render?: (value: T[keyof T]) => React.ReactNode;
  }

  interface DataTableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyExtractor: (item: T) => string;
    onRowClick?: (item: T) => void;
  }

  function DataTable<T>({
    data,
    columns,
    keyExtractor,
    onRowClick,
  }: DataTableProps<T>) {
    return (
      <table>
        <thead>
          <tr>{columns.map(col => <th key={col.header}>{col.header}</th>)}</tr>
        </thead>
        <tbody>
          {data.map(item => (
            <tr key={keyExtractor(item)} onClick={() => onRowClick?.(item)}>
              {columns.map(col => (
                <td key={String(col.accessor)}>
                  {col.render
                    ? col.render(item[col.accessor])
                    : String(item[col.accessor])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  // USAGE — TypeScript infers T = User automatically:
  <DataTable
    data={users}
    keyExtractor={u => u.id}
    columns={[
      { header: 'Name', accessor: 'name' },          // ✅ 'name' is keyof User
      { header: 'Email', accessor: 'email' },         // ✅
      { header: 'Role', accessor: 'role',
        render: (role) => <RoleBadge role={role} /> },
      { header: 'xyz', accessor: 'nonExistent' },     // ❌ TS error immediately
    ]}
  />
```

```
POLYMORPHIC COMPONENT ("as" prop):

  // Design system need: <Text> that renders as h1, h2, p, span, label
  // depending on usage context

  type PolymorphicProps<C extends React.ElementType> = {
    as?: C;
    children: React.ReactNode;
    className?: string;
  } & Omit<React.ComponentPropsWithoutRef<C>, 'as' | 'children'>;

  function Text<C extends React.ElementType = 'p'>({
    as,
    children,
    ...props
  }: PolymorphicProps<C>) {
    const Component = as ?? 'p';
    return <Component {...props}>{children}</Component>;
  }

  // TypeScript enforces correct props per HTML element:
  <Text as="h1">Page Title</Text>              // h1 props ✅
  <Text as="a" href="/about">About</Text>      // anchor + href ✅
  <Text as="button" onClick={fn}>Click</Text>  // button + onClick ✅
  <Text as="button" href="/x">broken</Text>    // href on button → TS error ❌
```

---
