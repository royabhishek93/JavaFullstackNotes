# Legacy Node.js Service Migration — Callback Hell to async/await
> **Topic:** Promisification | **Level:** Intermediate | **Frequency:** High

## The Setup

You inherit a Node.js service written in 2016. It reads a config file, connects to a database, runs a migration query, and writes an audit log. All four operations use `fs` and a database driver with error-first callbacks. The team wants to refactor to `async/await` without rewriting the database driver or changing the file system calls.

## The Question

Walk through the approach. Where do you apply promisification, and what does the before/after look like?

## Diagram

```
  BEFORE (callback hell, 5 levels deep):
  fs.readFile('config.json', 'utf8', (err, raw) => {
    if (err) return done(err);
    db.connect(JSON.parse(raw).url, (err, conn) => {
      if (err) return done(err);
      conn.query(MIGRATION_SQL, (err, result) => {
        if (err) return done(err);
        fs.writeFile('audit.log', JSON.stringify(result), (err) => {
          if (err) return done(err);
          done(null, result);
        });
      });
    });
  });

  AFTER (promisify once at module boundary):
  const readFile  = promisify(fs.readFile);
  const writeFile = promisify(fs.writeFile);
  const connect   = promisify(db.connect.bind(db));
  const query     = promisify(conn.query.bind(conn));

  async function runMigration() {
    const raw    = await readFile('config.json', 'utf8');
    const conn   = await connect(JSON.parse(raw).url);
    const result = await query(MIGRATION_SQL);
    await writeFile('audit.log', JSON.stringify(result));
    return result;
  }
```

## Model Answer (15 YOE)

The approach is: **promisify at the module boundary, once.** Do not scatter `new Promise()` constructors throughout the codebase — create promisified versions of the functions at the top of a dedicated adapter module, then import those everywhere.

```js
// adapters/fs.js — promisify the fs functions once
const { promisify } = require('util');
const fs = require('fs');

module.exports = {
  readFile:  promisify(fs.readFile),
  writeFile: promisify(fs.writeFile),
  mkdir:     promisify(fs.mkdir),
};
```

```js
// adapters/db.js — wrap legacy driver
const { promisify } = require('util');
const driver = require('legacy-db-driver');

const client = driver.createClient(process.env.DB_URL);

module.exports = {
  query:   promisify(client.query.bind(client)),
  connect: promisify(client.connect.bind(client)),
};
```

```js
// migration.js — clean async/await, no callbacks
const { readFile, writeFile } = require('./adapters/fs');
const db = require('./adapters/db');

async function runMigration() {
  const raw    = await readFile('config.json', 'utf8');
  const conn   = await db.connect(JSON.parse(raw).url);
  const result = await db.query(MIGRATION_SQL);
  await writeFile('audit.log', JSON.stringify(result));
  return result;
}
```

Two things to watch for. First, `.bind(client)` is critical. `util.promisify` preserves `this` context via `fn.apply(this, args)`, but if the driver's method relies on `this` pointing to the client instance, you must bind before passing to `promisify`. Forgetting `.bind` is a common runtime bug where the method throws "Cannot read property of undefined."

Second, for modern Node.js `fs`, skip `util.promisify` entirely and use `require('fs/promises')` — these are the officially pre-promisified versions and do not require any wrapping at all.

## Follow-up

**Q:** Why use `util.promisify` instead of writing `new Promise()` wrappers for each function?

**A:** `util.promisify` is a factory. It produces the wrapper in one line without repetition. Writing `new Promise()` around every callback function is fine for one or two cases, but at ten functions it is boilerplate that must be maintained. `util.promisify` also handles edge cases correctly: it uses `fn.apply(this, args)` to preserve the `this` context, and it checks for a `util.promisify.custom` symbol on the function, which lets library authors override the default behavior. Manual wrappers miss both.
