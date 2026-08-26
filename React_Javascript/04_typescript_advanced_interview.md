# TypeScript Advanced Interview Prep — 15 YOE Level

---

## 1. Big Picture: TypeScript Type System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TYPESCRIPT TYPE SYSTEM                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     TYPE UNIVERSE                                    │   │
│  │                                                                      │   │
│  │   unknown  ──── top type (everything assignable to unknown)          │   │
│  │      │                                                               │   │
│  │      ▼                                                               │   │
│  │   any  ──── escape hatch (assignable to/from everything) ⚠️          │   │
│  │      │                                                               │   │
│  │      ▼                                                               │   │
│  │   object / primitive types                                           │   │
│  │      │                                                               │   │
│  │      ▼                                                               │   │
│  │   never ──── bottom type (nothing assignable to never)               │   │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────┐    ┌──────────────────────────────────────────┐  │
│  │  STRUCTURAL TYPING   │    │         DECLARATION MERGING              │  │
│  │                      │    │                                          │  │
│  │  TS checks SHAPE,    │    │  interface Foo { a: string }             │  │
│  │  not names           │    │  interface Foo { b: number }  ← merges  │  │
│  │                      │    │  // Foo = { a: string; b: number }       │  │
│  │  { name, age } fits  │    │                                          │  │
│  │  Person if shape     │    │  type Foo = {...}  ← NO merge, error     │  │
│  │  matches             │    │                                          │  │
│  │                      │    │  Use case: augment 3rd-party modules     │  │
│  │  "Duck typing"       │    │  declare module 'express' { ... }        │  │
│  └──────────────────────┘    └──────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       GENERIC SYSTEM                                 │  │
│  │                                                                      │  │
│  │  Basic:        fn<T>(x: T): T                                        │  │
│  │  Constraint:   fn<T extends object>(x: T): keyof T                   │  │
│  │  Default:      fn<T = string>(x: T): T                               │  │
│  │  Conditional:  T extends U ? X : Y   (distributive over unions)      │  │
│  │  Infer:        T extends Promise<infer R> ? R : never                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       UTILITY TYPES MAP                              │  │
│  │                                                                      │  │
│  │  Partial<T>        → all props optional                              │  │
│  │  Required<T>       → all props required                              │  │
│  │  Readonly<T>       → all props readonly                              │  │
│  │  Pick<T, K>        → keep only K keys                                │  │
│  │  Omit<T, K>        → drop K keys                                     │  │
│  │  Record<K, V>      → object with K keys and V values                 │  │
│  │  Extract<T, U>     → T types assignable to U                         │  │
│  │  Exclude<T, U>     → T types NOT assignable to U                     │  │
│  │  ReturnType<F>     → infer return type of function F                 │  │
│  │  Parameters<F>     → infer param tuple of function F                 │  │
│  │  NonNullable<T>    → remove null | undefined from T                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Conversational Interview Script — How a 15-YOE Engineer Speaks

**Q: Walk me through how you think about TypeScript in a production system.**

> "TypeScript is a tool for building maintainable systems at scale. At 15 years in, I don't think of it as just 'JavaScript with types' — I think of it as a communication layer between engineers. The types are contracts. When I define an API response type or a domain model, I'm creating documentation that the compiler enforces. What I care about in production is: are we using `strict` mode everywhere? Are we avoiding `any` as a lint rule? Are we doing runtime validation at the edges — network boundaries, user input — and letting TypeScript take over from there? Tools like Zod let you define the schema once and derive the TypeScript type from it, so you're not maintaining the same contract in two places.

> The thing that separates junior from senior TypeScript thinking is understanding the difference between what the compiler knows and what actually happens at runtime. TypeScript types are erased. So `as User` doesn't check anything at runtime — you've just told the compiler to trust you. That's why I'm strict about where we use type assertions in code reviews."

---

**Q: When you're onboarding a new team to TypeScript, what are the first three things you enforce?**

> "First, `strict: true` in tsconfig — no exceptions. This enables `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, and others. Without `strictNullChecks`, you don't get half the safety TypeScript offers. Second, no `any` — we use ESLint's `@typescript-eslint/no-explicit-any` rule. If someone needs escape hatches they use `unknown` and then narrow it. Third, runtime validation at boundaries. TypeScript is compile-time only. Every network response, every environment variable, every form submission needs to be validated at runtime. We use Zod for this because it co-locates the schema and the type."

---

## 3. Scenario-Based Q&As — Production Context (8+ Questions)

---

**Q1: You're building an API client. How do you type the response to make it safe?**

**Answer:** Never trust the network. The pattern I use is Zod schema → inferred TypeScript type → validated parse.

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(["admin", "viewer", "editor"]),
  createdAt: z.string().datetime(),
});

type User = z.infer<typeof UserSchema>;

async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const raw = await res.json();
  return UserSchema.parse(raw); // throws ZodError if invalid
}
```

The key insight: `UserSchema.parse` throws a detailed error at runtime if the shape is wrong. The TypeScript type `User` is derived from the schema — single source of truth.

---

**Q2: How do you model a state machine in TypeScript — e.g., an order status flow?**

**Answer:** Discriminated unions. Each state is a tagged object. The discriminant is the `status` field.

```typescript
type OrderState =
  | { status: "pending"; orderId: string }
  | { status: "processing"; orderId: string; processorId: string }
  | { status: "shipped"; orderId: string; trackingNumber: string }
  | { status: "cancelled"; orderId: string; reason: string };

function describeOrder(order: OrderState): string {
  switch (order.status) {
    case "pending":     return `Pending: ${order.orderId}`;
    case "processing":  return `Processing by ${order.processorId}`;
    case "shipped":     return `Shipped: ${order.trackingNumber}`;
    case "cancelled":   return `Cancelled: ${order.reason}`;
    default:
      const _exhaustive: never = order; // compile error if case missed
      throw new Error(`Unhandled state: ${JSON.stringify(_exhaustive)}`);
  }
}
```

The `never` exhaustiveness check is critical. If someone adds a new `status` variant and forgets to handle it in this switch, TypeScript will error at compile time.

---

**Q3: A junior dev wrote `as SomeType` everywhere. How do you address it in code review?**

**Answer:** I explain the difference between type assertions and runtime safety. `as T` is a compile-time lie — you're bypassing the type checker, not performing a cast. At runtime, the value is exactly what it was. I replace it with a type guard or Zod parse.

```typescript
// BAD — no runtime check, can crash silently
const user = JSON.parse(data) as User;
console.log(user.email.toLowerCase()); // runtime error if email is missing

// GOOD — validated at runtime, type-safe after
const user = UserSchema.parse(JSON.parse(data));
console.log(user.email.toLowerCase()); // safe
```

---

**Q4: How would you build a type-safe event emitter?**

**Answer:** Use a generic event map and mapped types to enforce that each event name maps to the correct handler signature.

```typescript
type EventMap = {
  "user:login":  { userId: string; timestamp: number };
  "user:logout": { userId: string };
  "error":       { message: string; code: number };
};

class TypedEmitter<T extends Record<string, unknown>> {
  private handlers: Partial<{ [K in keyof T]: Array<(data: T[K]) => void> }> = {};

  on<K extends keyof T>(event: K, handler: (data: T[K]) => void): void {
    (this.handlers[event] ??= []).push(handler);
  }

  emit<K extends keyof T>(event: K, data: T[K]): void {
    this.handlers[event]?.forEach((h) => h(data));
  }
}

const emitter = new TypedEmitter<EventMap>();
emitter.on("user:login", ({ userId, timestamp }) => {
  console.log(userId, timestamp); // fully typed
});
```

---

**Q5: Explain how `satisfies` differs from a type annotation. When would you use it?**

**Answer:** A type annotation widens the inferred type to match the annotation. `satisfies` validates the value against the type but keeps the narrowest inferred type.

```typescript
type Config = Record<string, string | number>;

// With annotation — TypeScript widens, loses specific knowledge
const config1: Config = { port: 3000, host: "localhost" };
config1.port.toFixed(); // ERROR: port is string | number, not known to be number

// With satisfies — validates shape but keeps narrow types
const config2 = {
  port: 3000,
  host: "localhost",
} satisfies Config;
config2.port.toFixed(); // OK — TypeScript knows port is number
config2.host.toUpperCase(); // OK — TypeScript knows host is string
```

Use `satisfies` when you want to validate a literal object against a type but still retain the precise inferred type for downstream use. Very common in config objects and route maps.

---

**Q6: How do you use template literal types in practice?**

**Answer:** Template literal types let you compute string types from other string types. I use them most for event handler naming, CSS property keys, and API route patterns.

```typescript
type EventName = "click" | "focus" | "blur";
type EventHandler = `on${Capitalize<EventName>}`; 
// = "onClick" | "onFocus" | "onBlur"

type CSSProperty = "margin" | "padding";
type CSSDirection = "Top" | "Right" | "Bottom" | "Left";
type CSSKey = `${CSSProperty}${CSSDirection}`;
// = "marginTop" | "marginRight" | ... | "paddingLeft"

// Route typing for a REST API
type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";
type ApiRoute = `/api/${string}`;
type RouteKey = `${HttpMethod} ${ApiRoute}`;

const routes: Record<RouteKey, () => void> = {
  "GET /api/users": () => {},
  "POST /api/users": () => {},
};
```

---

**Q7: When would you use `Extract` vs `Exclude`?**

**Answer:** They're inverses for filtering union members.

```typescript
type Status = "active" | "inactive" | "pending" | "banned";

// Extract keeps what matches the second type
type ActiveStates = Extract<Status, "active" | "pending">;
// = "active" | "pending"

// Exclude removes what matches the second type
type NonBanned = Exclude<Status, "banned">;
// = "active" | "inactive" | "pending"

// Real use case: filtering action types in a reducer
type Action =
  | { type: "FETCH_USER"; id: string }
  | { type: "FETCH_POST"; id: string }
  | { type: "SET_THEME"; theme: string };

type FetchActions = Extract<Action, { type: `FETCH_${string}` }>;
// = { type: "FETCH_USER"; id: string } | { type: "FETCH_POST"; id: string }
```

---

**Q8: How do you handle optional chaining and nullability with strict TypeScript?**

**Answer:** With `strictNullChecks` on, TypeScript forces you to handle every potential null/undefined explicitly. The key patterns are: optional chaining `?.`, nullish coalescing `??`, and type narrowing with guards.

```typescript
interface Profile {
  address?: {
    city?: string;
    country: string;
  };
}

function getCity(profile: Profile): string {
  // Optional chaining + nullish coalescing
  return profile.address?.city ?? "Unknown";
}

// Assertion function when you're certain something is defined
function assertDefined<T>(val: T, name: string): asserts val is NonNullable<T> {
  if (val == null) throw new Error(`Expected ${name} to be defined`);
}

function processProfile(profile: Profile | null) {
  assertDefined(profile, "profile");
  // TypeScript now knows profile is Profile (not null)
  console.log(profile.address?.country);
}
```

---

## 4. Advanced Scenario Q&As (4+ Deep-Dive Questions)

---

**Q1: Explain conditional types and distributivity. When does distributivity cause bugs?**

**Answer:** Conditional types distribute over union types when the checked type is a naked type parameter. This is often what you want — but sometimes it isn't.

```typescript
// Distributive — T is naked type parameter
type IsString<T> = T extends string ? "yes" : "no";
type Result1 = IsString<string | number>;
// Distributes: IsString<string> | IsString<number>
// = "yes" | "no"  ← union

// Non-distributive — wrap in tuple to prevent distribution
type IsExactlyString<T> = [T] extends [string] ? "yes" : "no";
type Result2 = IsExactlyString<string | number>;
// Does NOT distribute: [string | number] extends [string] = false
// = "no"  ← single result

// Infer inside conditionals — very powerful for unwrapping
type Awaited<T> = T extends Promise<infer R> ? Awaited<R> : T;
type A = Awaited<Promise<Promise<string>>>; // = string

// Real use case: extracting function overload return types
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
type ApiResult = UnwrapPromise<ReturnType<typeof fetchUser>>; // = User
```

Distributivity bugs appear when you want to check "is this entire union assignable to X" but you accidentally write a distributive check that checks each member separately.

---

**Q2: How do you implement a deep readonly type recursively?**

**Answer:** Use mapped types recursively with conditional types to handle primitives as base cases.

```typescript
type Primitive = string | number | boolean | null | undefined | symbol | bigint;

type DeepReadonly<T> = T extends Primitive
  ? T
  : T extends Array<infer U>
  ? ReadonlyArray<DeepReadonly<U>>
  : T extends Map<infer K, infer V>
  ? ReadonlyMap<K, DeepReadonly<V>>
  : T extends Set<infer U>
  ? ReadonlySet<DeepReadonly<U>>
  : { readonly [K in keyof T]: DeepReadonly<T[K]> };

interface AppState {
  user: { name: string; address: { city: string } };
  items: string[];
}

type ReadonlyState = DeepReadonly<AppState>;
// ReadonlyState.user is readonly
// ReadonlyState.user.address is readonly
// ReadonlyState.items is ReadonlyArray<string>
```

This is used in Redux-style architectures where you want the state tree to be immutable at every level. TypeScript's built-in `Readonly<T>` is only one level deep.

---

**Q3: How does `strictFunctionTypes` affect contravariance? Why does it matter for callbacks?**

**Answer:** With `strictFunctionTypes`, TypeScript enforces contravariance for function parameter types. This prevents a class of bugs where a more-specific callback is used where a less-specific one is expected.

```typescript
type Logger = (message: string) => void;
type VerboseLogger = (message: string, metadata: object) => void;

// Without strict: VerboseLogger assignable to Logger (unsound)
// With strictFunctionTypes: ERROR — VerboseLogger requires 2 args, Logger provides 1

// Correct mental model:
// If function expects Animal handler, you CAN pass Dog handler
// If function expects Dog handler, you CANNOT pass Animal handler
// (because callers might pass non-Dog animals)

class Animal { breathe() {} }
class Dog extends Animal { bark() {} }

type AnimalHandler = (a: Animal) => void;
type DogHandler = (d: Dog) => void;

let animalHandler: AnimalHandler = (a) => a.breathe();
let dogHandler: DogHandler = (d) => d.bark();

// DogHandler NOT assignable to AnimalHandler (contravariant in params)
// Because: if we use dogHandler as animalHandler, caller might pass Cat
// and then d.bark() would fail at runtime
```

This matters most in event systems and higher-order functions where callbacks are passed around.

---

**Q4: How do you use declaration merging to augment a third-party library's types?**

**Answer:** Module augmentation lets you extend existing types without forking them. This is how you add custom properties to Express's `Request`, extend Vuex store types, or add custom methods to Mongoose documents.

```typescript
// Augmenting Express Request to add our auth user
// In a file: src/types/express.d.ts

import "express";

declare module "express-serve-static-core" {
  interface Request {
    user?: {
      id: string;
      email: string;
      roles: string[];
    };
  }
}

// Now in any Express handler:
import { Request, Response } from "express";

export function requireAuth(req: Request, res: Response, next: Function) {
  if (!req.user) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

// After requireAuth middleware, req.user is defined
// You can create a type guard or use assertion to narrow it
```

The key is `declare module` with the exact module string the library uses. For `@types/express` this is `express-serve-static-core`. You discover this by looking at the type definitions.

---

## 5. Senior Trap Questions — 6 Traps with Exact Mistakes Named

---

### Trap 1: "You should always prefer `interface` over `type`"

**The Trap:** Candidates repeat the old TypeScript style guide advice without knowing why or when it's wrong.

**Why it's wrong:**

```typescript
// Types can do things interfaces CANNOT:

// 1. Union types — interfaces can't do this
type Status = "active" | "inactive" | "pending";
// interface Status = ??? — impossible

// 2. Computed/mapped types
type ReadonlyUser = Readonly<User>; // easy with type
// interface ReadonlyUser extends Readonly<User> {} — more verbose, less flexible

// 3. Tuple types
type Pair = [string, number];
// interface Pair — can approximate but awkward

// Interfaces CAN do something types can't: declaration merging
interface Window { myCustomProp: string; } // merges with existing Window
type Window = { myCustomProp: string; }; // ERROR: duplicate identifier

// CORRECT ANSWER:
// Use interface when: you need declaration merging, you're defining a class contract
// Use type when: unions, intersections, computed types, mapped types, tuples
// In practice: types are more flexible; use them by default unless you need merging
```

**Correct answer:** The choice depends on the use case. `interface` is for OOP-style contracts and when you need declaration merging. `type` is more powerful for everything else — unions, computed types, mapped types.

---

### Trap 2: "`any` and `unknown` are basically the same — both accept anything"

**The Trap:** Candidates know both accept any value but don't understand the critical difference in how you use the value afterward.

**Why it's wrong:**

```typescript
// any: bypasses ALL type checking — you can do anything with it
function processAny(x: any) {
  x.foo.bar.baz(); // TypeScript is silent — this might crash at runtime
  x * 100;         // no error
  x.nonExistentMethod(); // no error — this is dangerous
}

// unknown: forces you to NARROW before using
function processUnknown(x: unknown) {
  x.foo; // ERROR: Object is of type 'unknown'
  
  if (typeof x === "string") {
    x.toUpperCase(); // OK — narrowed to string
  }
  
  if (x instanceof Error) {
    x.message; // OK — narrowed to Error
  }
}

// CORRECT ANSWER:
// any = "trust me, I know what this is" — bypasses the type system entirely
// unknown = "I don't know yet" — forces you to prove what it is before using it
// Use unknown for: JSON.parse results, catch(e) errors, library interop
// Use any: almost never in production code
```

---

### Trap 3: "Type assertions (`as`) are like casts — they verify the type"

**The Trap:** Candidates from Java/C# backgrounds assume `as User` performs a runtime check like a Java cast. It does not.

**Why it's wrong:**

```typescript
// Java: (User) obj throws ClassCastException if obj is not a User
// TypeScript: (obj as User) DOES NOTHING AT RUNTIME

const raw: unknown = { name: "Bob" }; // no email field

// This compiles and runs without error
const user = raw as { name: string; email: string };
console.log(user.email.toLowerCase()); // RUNTIME ERROR: Cannot read properties of undefined

// Double assertion bypasses even stricter checks
const n = 42 as unknown as string; // compiles fine — the compiler trusts you twice

// CORRECT PATTERN: use type guards or runtime validation
function isUser(x: unknown): x is { name: string; email: string } {
  return (
    typeof x === "object" &&
    x !== null &&
    "name" in x &&
    "email" in x &&
    typeof (x as any).email === "string"
  );
}

if (isUser(raw)) {
  console.log(raw.email.toLowerCase()); // safe
}
```

**Correct answer:** Type assertions are instructions to the compiler, not runtime checks. Use them only when you have information the compiler doesn't — and document why. For untrusted data, use Zod parse or a type guard.

---

### Trap 4: "Generics are just templates/macros like in C++"

**The Trap:** Candidates think generics are simple placeholder substitution and miss the power of constraints, conditional types, and inference.

**Why it's wrong:**

```typescript
// Generics with constraints — enforce structure, not just "any type"
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]; // TypeScript knows the return type is T[K]
}

const user = { name: "Alice", age: 30 };
const name = getProperty(user, "name"); // type: string
const age = getProperty(user, "age");   // type: number
// getProperty(user, "foo") — ERROR at compile time

// Generic variance matters — TypeScript checks assignability
type Producer<T> = () => T;  // covariant in T
type Consumer<T> = (x: T) => void; // contravariant in T

// Conditional types based on generics — not possible with C++ templates
type IsArray<T> = T extends any[] ? "array" : "not array";
type A = IsArray<string[]>; // "array"
type B = IsArray<string>;   // "not array"

// Inference FROM generics using infer
type ElementOf<T> = T extends (infer U)[] ? U : never;
type E = ElementOf<string[]>; // = string
type F = ElementOf<[number, boolean]>; // = number | boolean
```

**Correct answer:** TypeScript generics support constraint-based reasoning, conditional type logic, and type inference. They're far more powerful than C++ template substitution.

---

### Trap 5: "Enums are just objects — same as `const` objects"

**The Trap:** Candidates use enums as drop-in replacements for union types without knowing the runtime and build-system implications.

**Why it's wrong:**

```typescript
// Numeric enum — has REVERSE MAPPING at runtime
enum Direction {
  Up = 0,
  Down = 1,
}
// At runtime: Direction[0] === "Up" AND Direction["Up"] === 0
// This is a bidirectional map — unexpected behavior for most

// String enum — no reverse mapping, but still adds runtime code
enum Role {
  Admin = "ADMIN",
  Viewer = "VIEWER",
}
// At runtime: becomes an actual object in the bundle

// const enum — inlined at compile time, no runtime object
const enum HttpStatus {
  OK = 200,
  NotFound = 404,
}
// BUT: const enums break with isolatedModules (Babel, ESBuild, Vite)
// Because those tools transpile per-file and can't inline cross-file

// BETTER for most production code: union of string literals
type Role = "ADMIN" | "VIEWER";
// Zero runtime cost, no reverse mapping confusion, works everywhere
// Supports exhaustiveness checking the same way

// When to use real enums:
// - You need the runtime object for iteration
// - You're sure your build pipeline handles them correctly
```

**Correct answer:** Enums compile to JavaScript objects with bidirectional mappings (for numeric enums). `const enum` has build-tool compatibility issues. For most cases, string union types are safer, tree-shakeable, and equally type-safe.

---

### Trap 6: "Intersection types just combine properties like merging two objects"

**The Trap:** Candidates think `A & B` always works like `Object.assign(a, b)`. It doesn't — especially with conflicting primitive properties.

**Why it's wrong:**

```typescript
// Merging compatible interfaces — works as expected
type A = { name: string; age: number };
type B = { email: string; role: string };
type C = A & B;
// C = { name: string; age: number; email: string; role: string }

// Conflicting primitive types → never
type D = { id: string };
type E = { id: number };
type F = D & E;
// F.id is string & number = never
// F is effectively impossible to satisfy

const bad: F = { id: "hello" }; // ERROR
const alsoBad: F = { id: 42 }; // ERROR

// This often happens in large codebases with generated types
// and function overloads — the intersection silently becomes never
// and you only discover it when you try to use the value

// CORRECT MENTAL MODEL:
// Intersection means "satisfies both constraints simultaneously"
// For object types with compatible non-overlapping keys: looks like a merge
// For types with conflicting property types: narrows to never
// For function types: creates an overloaded function signature
```

**Correct answer:** Intersection `A & B` means a value must satisfy both `A` and `B` simultaneously. For objects with overlapping primitive keys, the property type becomes the intersection of those primitives — which can be `never` if they're incompatible. This is a common source of subtle bugs.

---

## 6. Production Code Examples

### Form Validation with Type-Safe Error Handling

```typescript
import { z } from "zod";

const SignupSchema = z.object({
  email:    z.string().email("Invalid email"),
  password: z.string().min(8, "Min 8 characters"),
  role:     z.enum(["admin", "user"]).default("user"),
});

type SignupInput = z.infer<typeof SignupSchema>;
type FormErrors = Partial<Record<keyof SignupInput, string>>;

function validateSignup(raw: unknown): 
  | { success: true; data: SignupInput }
  | { success: false; errors: FormErrors } {
  const result = SignupSchema.safeParse(raw);
  if (result.success) return { success: true, data: result.data };
  const errors: FormErrors = {};
  result.error.errors.forEach((e) => {
    const key = e.path[0] as keyof SignupInput;
    errors[key] = e.message;
  });
  return { success: false, errors };
}
```

---

### Type-Safe Redux Slice Pattern

```typescript
type AsyncStatus = "idle" | "loading" | "success" | "error";

type UserState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; user: User }
  | { status: "error"; message: string };

type UserAction =
  | { type: "FETCH_USER_START" }
  | { type: "FETCH_USER_SUCCESS"; payload: User }
  | { type: "FETCH_USER_FAILURE"; payload: string };

function userReducer(state: UserState, action: UserAction): UserState {
  switch (action.type) {
    case "FETCH_USER_START":   return { status: "loading" };
    case "FETCH_USER_SUCCESS": return { status: "success", user: action.payload };
    case "FETCH_USER_FAILURE": return { status: "error", message: action.payload };
    default:
      const _: never = action;
      return state;
  }
}
```

---

### Generic Repository Pattern

```typescript
interface Repository<T extends { id: string }> {
  findById(id: string): Promise<T | null>;
  findMany(filter: Partial<T>): Promise<T[]>;
  save(entity: T): Promise<T>;
  delete(id: string): Promise<void>;
}

class InMemoryRepository<T extends { id: string }> 
  implements Repository<T> {
  private store = new Map<string, T>();

  async findById(id: string): Promise<T | null> {
    return this.store.get(id) ?? null;
  }

  async findMany(filter: Partial<T>): Promise<T[]> {
    return [...this.store.values()].filter((item) =>
      (Object.keys(filter) as Array<keyof T>).every(
        (key) => item[key] === filter[key]
      )
    );
  }

  async save(entity: T): Promise<T> {
    this.store.set(entity.id, entity);
    return entity;
  }

  async delete(id: string): Promise<void> {
    this.store.delete(id);
  }
}
```

---

### Builder Pattern with Fluent API Types

```typescript
class QueryBuilder<T> {
  private _where: Partial<T> = {};
  private _limit = 100;
  private _offset = 0;

  where(filter: Partial<T>): this {
    this._where = { ...this._where, ...filter };
    return this;
  }

  limit(n: number): this {
    this._limit = n;
    return this;
  }

  offset(n: number): this {
    this._offset = n;
    return this;
  }

  build(): { where: Partial<T>; limit: number; offset: number } {
    return { where: this._where, limit: this._limit, offset: this._offset };
  }
}

// Usage — fully type-safe, no any
const query = new QueryBuilder<User>()
  .where({ role: "admin" })
  .limit(10)
  .offset(20)
  .build();
```

---

### Const Assertions for Lookup Tables

```typescript
const HTTP_STATUS = {
  OK:          200,
  CREATED:     201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  NOT_FOUND:   404,
  SERVER_ERROR: 500,
} as const;

type HttpStatusCode = typeof HTTP_STATUS[keyof typeof HTTP_STATUS];
// = 200 | 201 | 400 | 401 | 404 | 500 — literal number union

function isSuccess(code: HttpStatusCode): boolean {
  return code >= 200 && code < 300;
}

// Without 'as const', HTTP_STATUS[keyof typeof HTTP_STATUS] would be 'number'
// With 'as const', you get the exact literal types
```

---

### Type-Safe Environment Variables

```typescript
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV:     z.enum(["development", "production", "test"]),
  DATABASE_URL: z.string().url(),
  PORT:         z.coerce.number().min(1).max(65535).default(3000),
  JWT_SECRET:   z.string().min(32),
  LOG_LEVEL:    z.enum(["debug", "info", "warn", "error"]).default("info"),
});

type Env = z.infer<typeof EnvSchema>;

// Call once at app startup — crash immediately if env is misconfigured
function loadEnv(): Env {
  const result = EnvSchema.safeParse(process.env);
  if (!result.success) {
    console.error("Invalid environment variables:");
    result.error.errors.forEach((e) => {
      console.error(`  ${e.path.join(".")}: ${e.message}`);
    });
    process.exit(1);
  }
  return result.data;
}

export const env = loadEnv();
// env.PORT is typed as number, env.NODE_ENV is typed as the literal union
```

---

## 7. Interview Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TYPESCRIPT INTERVIEW CHEAT SHEET                 │
│                         15-YOE Level                                │
├─────────────────────────────────────────────────────────────────────┤
│  CORE CONCEPTS                                                      │
│  • Structural typing — shape match, not name match                  │
│  • Type erasure — types don't exist at runtime                      │
│  • Strict mode — always on in production: strictNullChecks,         │
│    noImplicitAny, strictFunctionTypes                               │
│  • Runtime validation — Zod at boundaries, TypeScript inside        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  GENERICS QUICK REF                                                 │
│  <T extends K>      — T must be assignable to K                     │
│  <T = Default>      — default type if not specified                 │
│  T extends U ? X : Y — conditional type (distributes over unions)  │
│  [T] extends [U]    — non-distributive conditional                  │
│  T extends X ? infer R : never — extract inner type                │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  UTILITY TYPES                                                      │
│  Partial<T>         — all optional                                  │
│  Required<T>        — all required                                  │
│  Readonly<T>        — all readonly (1 level)                        │
│  Pick<T, K>         — keep K keys                                   │
│  Omit<T, K>         — drop K keys                                   │
│  Record<K, V>       — object with K keys, V values                  │
│  Extract<T, U>      — T members assignable to U                     │
│  Exclude<T, U>      — T members NOT assignable to U                 │
│  ReturnType<F>      — function return type                          │
│  Parameters<F>      — function params as tuple                      │
│  NonNullable<T>     — remove null | undefined                       │
│  Awaited<T>         — unwrap Promise (recursive)                    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  TYPE GUARDS                                                        │
│  typeof x === "string"          — primitive narrowing               │
│  x instanceof MyClass           — class instance narrowing          │
│  "key" in obj                   — property existence check          │
│  (x): x is SomeType => boolean  — user-defined type guard           │
│  (x): asserts x is T            — assertion function (throws)       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  DISCRIMINATED UNIONS                                               │
│  • Common literal field (discriminant) — usually "type"/"status"   │
│  • Switch on discriminant — exhaustiveness via never check          │
│  • const _: never = x in default branch catches missing cases       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  COMMON TRAPS                                                       │
│  as Type        — NO runtime check, just compiler instruction       │
│  any            — bypasses all checks, avoid completely             │
│  unknown        — forces narrowing, use instead of any              │
│  interface      — for merging/OOP; type — for unions/computed       │
│  enum           — has runtime overhead; prefer string unions        │
│  A & B          — conflicting primitive props → never               │
│  satisfies      — validates without widening (TS 4.9+)             │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  MAPPED TYPES SYNTAX                                                │
│  { [K in keyof T]: T[K] }               — identity mapped type     │
│  { [K in keyof T]?: T[K] }              — all optional             │
│  { readonly [K in keyof T]: T[K] }      — all readonly             │
│  { [K in keyof T]-?: T[K] }             — remove optional (Required)│
│  { [K in keyof T as NewK]: T[K] }       — key remapping (TS 4.1+)  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  TEMPLATE LITERAL TYPES                                             │
│  `on${Capitalize<EventName>}` — derive event handler names          │
│  `${HttpMethod} ${ApiRoute}` — typed route registry keys            │
│  Uppercase<T>, Lowercase<T>, Capitalize<T>, Uncapitalize<T>         │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  DECLARATION MERGING RULES                                          │
│  interface + interface → merges (all interfaces same name merge)    │
│  type + type           → ERROR (duplicate identifier)               │
│  declare module 'x'    → augment external module types              │
│  namespace + namespace → merges                                     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  AS CONST                                                           │
│  { a: 1 } as const        → { readonly a: 1 } (literal)            │
│  ["a", "b"] as const      → readonly ["a", "b"] tuple              │
│  Enables: exact literal types, tuple types, const enums alternative │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ANSWER FRAMEWORK FOR INTERVIEWS                                    │
│  1. Start with the principle/why                                    │
│  2. Show the correct code                                           │
│  3. Name the trap/mistake explicitly                                │
│  4. Connect to production impact (runtime crash, bundle size, etc.) │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Key Interview Phrases That Signal Seniority

- "TypeScript types are erased at runtime — I treat the boundary between compile-time and runtime as a hard line"
- "I use Zod at trust boundaries — network, user input, env vars — and let TypeScript handle the rest"
- "The `never` type in a default branch is not defensive coding, it's compile-time exhaustiveness enforcement"
- "I distinguish between widening a type (annotation) and validating without widening (satisfies)"
- "Declaration merging is how you extend third-party types — it's the intentional design, not a workaround"
- "Distributive conditional types catch people off guard — I use tuple wrapping when I need non-distributive behavior"
- "With `strictFunctionTypes`, callback parameters are contravariant — this prevents a real class of bugs"
- "`as const` is one of my favorite features for config objects — you get literal types without an explicit type annotation"
