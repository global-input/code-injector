# 4. Building a definition project

[← Back to index](../README.md)

A **definition project** is a normal Python package that owns _what_ to inject and
_where_. It contains two kinds of artefact:

1. **Aspect dictionaries** — Python modules exposing `aspects` lists (the rules).
2. **Advisors / payload code** — the actual code that gets injected or copied.

The engine never imports your definition project directly; the **driver** does, after
you put the project on `PYTHONPATH`. So a definition project's only hard requirement is:
_be importable, and expose `aspects` lists in modules the driver names._

## Layout Example

```
aspect-project/
├── html5App/
│   └── aspects/
│       ├── logging.py          # aspect dicts: where logging is woven in
│       ├── autosignin.py       # aspect dicts: auto sign-in (dev/perf/test only)
│       ├── performance.py      # aspect dicts: performance instrumentation
│       ├── httpRequest.py
│       ├── setversions.py
│       ├── advisors/           # the JS "advisors" that the advice calls into
│       │   └── remote-log/     # a library copied into the target project
│       ├── fixes/              # build-fix aspect groups
│       ├── build/              # prebuild preparation aspects
│       └── …                   # adobe/, conviva/, kantar/, video/, youview/, …
├── lib/
│   └── remoteLogs.js           # static lib copied into the target as src/static/remoteLogs.js
└── patches/                    # raw .patch files for changes too large for aspects
```

Key points:

- The driver imports these as `html5App.aspects.<module>` (e.g.
  `import html5App.aspects.logging`). That works because the aspect project is on
  `PYTHONPATH`, making `html5App` a top-level package. **The folder name `html5App`
  therefore matters** — it is the import root the driver expects.
- Subfolders (`fixes/`, `build/`, `adobe/`, …) just group related aspect modules; the
  driver imports whichever ones a given job needs.

## Writing an aspect module

A module is just Python that ends with a list called `aspects` (the name the driver
passes to `runAspectIn`). Minimal:

```python
# html5App/aspects/mytrace.py
aspects = [
    {
        "file": "src/app/boot.js",
        "aspects": [{
            "pointcut": "function boot() {",
            "advice":  "remoteLog.trace('boot');",
            "position": "after"
        }]
    }
]
```

Because it is real Python you can:

- import config to parameterise advice (`import html5.config` then
  `html5.config.tracingOptions…`);
- `.format(...)` values into advice strings;
- build the list conditionally, `extend()` it from several blocks, generate it in a
  loop, etc.

See [03-aspect-reference.md](03-aspect-reference.md) for every key you can use.

## Advisors / payload code

"Advice" in the aspect dict is usually a _small_ hook that calls into a _larger_ body of
code you ship with the definition project. Two common patterns :

- **Copy a folder once, then weave imports/calls.** The driver calls
  `fileutil.copyFolderIfEmpty(source, dest, minFiles)` to drop the advisor library
  (e.g. `advisors/remote-log` → `<target>/remote-log`) into the target, then runs the
  aspects that wire it up. (`copyRemoteLogFolder` in the driver.)
- **Copy a single static file, then weave.** `lib/remoteLogs.js` is copied to
  `<target>/src/static/remoteLogs.js`, then aspects reference it.
  (`copyStaticRemoteLogFile` in the driver.)

This keeps the _injected lines_ tiny (just a call or import) while the _substance_ lives
as ordinary, testable source in the definition project.

## When an aspect is the wrong tool: patches

For changes too large or too structural for text pointcuts (e.g. multi-file vendor
edits), `.../patches/<branch>/<ticket>/…` stores raw `.patch` files applied by
the driver/build outside the injector. Treat patches as the escape hatch; prefer
aspects for anything you want to keep readable and condition-aware.

## Design guidance

- **Keep advice minimal and idempotent.** Inject a call, not a body. The default
  `skip-if-advice-found` then protects you from double injection.
- **Gate by `env`/`branch`** so debug-only concerns never reach production builds.
- **Mark fragile pointcuts `optional`** so a refactor in the main project degrades
  gracefully instead of failing the build — but only where a silent skip is acceptable.
- **Prefer `match-type: function`** when wrapping calls whose arguments you don't want
  to hard-code.

Continue to **[05-wiring-an-app.md](05-wiring-an-app.md)**.
