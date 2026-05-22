# 2. Engine architecture

[← Back to index](../README.md)

The engine is the `codeInjector/` Python package. It is **generic**: it contains no
reference to any specific project. Below, each module is described with its public
surface and the behaviour that matters when you write aspects.

```
codeInjector/
├── context.py          # per-app build context (branch / version / env)
├── aspectConditions.py # decides IF an aspect should run
├── aspectHandlers.py   # performs the weaving (pointcut → advice)
├── aspectRunners.py    # the top-level loop over files and aspects
├── textUtil.py         # text search + newline-aware insert/replace/remove
├── fileutil.py         # read / write / copy files & folders
└── printers.py         # coloured console output
```

The call flow for one run is:

```
runAspectIn(aspects, folder, onEachFile, context)        # aspectRunners.py
   for each aspect-group (one target file):
      checkAspectCondition(group, context, file)         # aspectConditions.py  → skip?
      content = readFile(folder/file)                    # fileutil.py
      for each inner aspect:
         checkAspectCondition(inner, context, file, content)  → skip?
         handleAspect(inner, content, context)           # aspectHandlers.py → new content
         (if pointcut not found and match-type=function: copy params and retry)
         onEachFile(inner, file, content)                # caller's post-process hook
      writeFile(folder/file, content)                    # fileutil.py
```

---

## context.py

Holds the build context per "app" (an app is just a named target, e.g. `html5`,
`uwp`, `cast`).

- `ContextInfo` — fields `branch`, `version`, `env`.
- `apps` — a module-level dict `{appName: ContextInfo}`.
- `createApp(appName, branch, version, env)` — registers/updates an app's context.
  Called once per run from the CLI argument processor.
- `getAppContext(appName)` — fetch (creating an empty one if needed).
- `setVersionSuffix(appName, versionSuffix)` — adjust the version string:
  - if `versionSuffix` starts with `REPLACE:` → the version is **replaced** by the text
    after the prefix;
  - otherwise the text is **appended** to the existing version.
    This is how `options/*.json` can tag a build (e.g. append `-perf`) — see
    [06-running.md](06-running.md#options-json).

---

## aspectConditions.py

`checkAspectCondition(aspect, context, file, content=None)` returns `True` if the
aspect should be applied. It is called twice: once on the **aspect group** (with no
`content`, before the file is read) and once on each **inner aspect** (with `content`).

Conditions, in evaluation order:

| Key                               | Effect                                                                                                                                                                                                                                                                                               |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disabled: True`                  | Always skip.                                                                                                                                                                                                                                                                                         |
| `env`                             | Must match `context.env`. String = equality; list = membership.                                                                                                                                                                                                                                      |
| `branch`                          | Must match `context.branch` (string or list).                                                                                                                                                                                                                                                        |
| `branch-to-skip`                  | Skip if it matches `context.branch`.                                                                                                                                                                                                                                                                 |
| `skip-if-file-not-found: True`    | Skip if the target file does not exist on disk.                                                                                                                                                                                                                                                      |
| `skip-if-not-found`               | (needs `content`) Skip unless the given text(s) are present. String or list — for a list, _all_ must be present.                                                                                                                                                                                     |
| `skip-if-found`                   | (needs `content`) Skip if the given text(s) are present. String or list — any match skips.                                                                                                                                                                                                           |
| `advice` + `skip-if-advice-found` | If `skip-if-found` is not set, the engine derives an idempotency check from the advice itself: if the advice text is already in the file, skip. Controlled by `skip-if-advice-found` (default `True`) and `trim-advice` (default `True`). Works for both string advice and `{before, after}` advice. |

The `advice`-derived check is what makes injection **idempotent** by default: running
twice will not double-inject, because the second run sees its own advice already
present and skips.

`contextMatch(valueInAspect, valueInContext, illegalTypeValue)` implements the
string-equality / list-membership comparison used for `env` and `branch`.

---

## aspectHandlers.py

The weaver. `handleAspect(aspect, content, context)` returns `(message, newContent)`;
an empty `message` means success, a non-empty one is an error string.

Pointcut handling:

- `pointcut` missing → error.
- `pointcut == '@aspect'` → delegate to `handleAnnotatedAspect` (inline annotation
  mode, below).
- otherwise the pointcut is searched repeatedly through the file (so **every**
  occurrence is processed, not just the first).

`match-type` (default `exact`):

- `exact` — literal text search.
- `regex` — `re.search` pattern.
- `function` — literal search, but with the special argument-copying retry handled in
  `aspectRunners.py` (see below).

`position` decides what happens at each match:

| `position`         | Behaviour                                   |
| ------------------ | ------------------------------------------- |
| `before` (default) | Insert advice immediately before the match. |
| `after`            | Insert advice immediately after the match.  |
| `replace`          | Replace the matched text with the advice.   |
| `remove`           | Delete the matched text (no advice needed). |

`advice` may be:

- a **string** — inserted/replacing as above; or
- a **dict `{before, after}`** — wrap the match with `before` text in front and `after`
  text behind (either side may be omitted).

`trim-pointcut` / `trim-advice` (both default `True`) strip surrounding whitespace from
the multi-line triple-quoted strings that are convenient to write in Python.

`optional: True` — if the pointcut is never found, succeed silently instead of
returning a "not found" error.

### handleAnnotatedAspect (`pointcut == '@aspect'`)

Activates code that is parked inside the target file as a comment:

```js
/* @aspect'''
    remoteLog.trace('here');
''' */
```

The engine finds each comment, looks for the `@aspect''' … '''` annotation inside it,
and rewrites the file so the comment markers are removed and the inner text becomes
live code. This lets you keep large advice next to the code it touches.

### addRemoteLog (helper)

A project-specific convenience used as an `onEachFile` post-processor: if an aspect's
advice references `remoteLog`, it ensures the file has
`import * as remoteLog from '~/remote-log';` at the top (inserted after the existing
import block via `textUtil.insertImportStatement`). It is idempotent.

---

## aspectRunners.py

`runAspectIn(aspects, folder, onEachFile, context)` is the entry point a driver calls.

- Iterates the list of aspect groups; for each, resolves `folder + '/' + file`.
- Skips groups whose group-level conditions fail.
- Reads the file once, applies every inner aspect in order, then writes it back.
- **Function-call retry**: if `handleAspect` reports the pointcut "not found" _and_ the
  aspect uses `match-type: function`, it calls `processPointFunctionCall`, which uses
  `textUtil.copyInputParameters` to copy the _actual_ argument list from the target's
  function call into both the pointcut and the advice, then retries. This lets you
  rewrite `foo(a, b, c)` → `wrap(foo, a, b, c)` without knowing the arguments in
  advance.
- `onEachFile(aspect, file, content)` is the caller's hook, run after a successful
  weave — used for linting and the `remoteLog` import injection in the real driver.
- Errors are printed via `printers.printError` (the file is still written with whatever
  succeeded).

---

## textUtil.py

The text-manipulation core.

- **`ContentRange`** wraps the file content and a moving `[start, end)` cursor. Its
  insert/replace/remove methods keep the cursor positioned correctly so repeated
  matches advance through the file. Crucially, `getSeparators` inspects the surrounding
  characters and adds `\n` only where needed, so injected lines land on their own line
  without creating blank-line noise.
- **`findText(contentRange, textToFind, matchType)`** — `exact`/`function` use literal
  `find`; `regex` uses `re.search`.
- **`findComment` / `findAdviceAnnotation`** — locate `//` and `/* */` comments and the
  `@aspect''' '''` annotation for inline-aspect mode.
- **`insertImportStatement` / `findHeadStatementInsertPosition`** — find the end of the
  leading `import …;` block (skipping `//` and `/* */` comments) and insert a new import
  there.
- **`copyInputParameters` / `parse_parentheses` / `replace_parameters`** — the
  machinery behind `match-type: function`.

---

## fileutil.py & printers.py

- `fileutil.readFile` / `writeFile` — plain text IO.
- `fileutil.copyFolderIfEmpty(source, target, minNumberOfFilesInDest)` — copy a folder
  (e.g. the injected `remote-log` library) into the target project only if it isn't
  already there. Used by the driver to seed advisor code before weaving.
- `printers.printError` / `printInfo` — coloured console messages. Note the driver
  treats **any** stdout/stderr from the Python process as a failure signal (see
  [06-running.md](06-running.md)), so the engine stays quiet on success.

Continue to **[03-aspect-reference.md](03-aspect-reference.md)**.
