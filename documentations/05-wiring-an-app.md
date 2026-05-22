# 5. Wiring an app / driver layer

[← Back to index](../README.md)

The **driver/app layer** turns build/deploy parameters into engine calls. It answers:
_for this `--app` and `--job`, which aspect modules do I import, and how do I run them?_

There are two concrete examples in the codebase:

- **The bundled minimal demo** — `code-injector/html5/` + `code-injector/__main__.py`.
- **The real deployment driver** — `aspects/pythons/` (`index.py`,
  `html5/{config,actions,trackingOption}.py`, `options/*.json`) under
  `.../aspects/`.

Both follow the same three-part shape: an **entry point** that parses args, a **config**
that locates the target and definition projects, and an **actions** class that maps jobs
to aspect runs.

---

## 5.1 The entry point (`index.py` / `__main__.py`)

Parses CLI options, builds the context, dispatches to the app action.

Demo (`__main__.py`) accepts: `--app --branch --version --env --job`.
Real driver (`index.py`) adds: `--options` and `--extra`.

```python
# simplified from the real index.py
configArguments = ['branch=', 'version=', 'env=', 'job=', 'app=', 'options=', 'extra=']

class ArgumentProcessor:
    def processArguments(self, argv):
        opts, _ = getopt.getopt(argv, "", configArguments)
        for opt, arg in opts:
            ...   # store branch/version/env/job/app/options/extra
        codeInjector.context.createApp(self.app, self.branch, self.version, self.env)

    def execute(self):
        appAction = self.createAppAction(self.app)   # html5 / uwp / cast / poc
        self.loadJsonOption(appAction, self.options) # read options/*.json, set tracingOptions + versionSuffix
        appAction.execute(self.extra)
```

Two responsibilities worth noting:

- `createApp(...)` seeds the build **context** (env/branch/version) the engine will use
  for condition checks.
- `loadJsonOption(...)` reads `options/<name>.json`, feeds it to
  `appAction.setTracingOptions(...)`, and — if the JSON has a `context.versionSuffix` —
  calls `context.setVersionSuffix(...)` (append, or replace via the `REPLACE:` prefix).

---

## 5.2 Config (`config.py`)

Locates the **target project** and points at the **definition project**.

Demo:

```python
name   = 'html5'
folder = "./sampleCode"        # the target project to edit
```

Real:

```python
name   = 'html5'
folder = os.environ.get('react_html5_projectfolder')   # target taken from the build env
aspects   = "/…/html5App/aspects"           # definition project paths
advistors = "/…/html5App/aspects/advisors"
# + helpers describing files to copy in (remote-log folder, remoteLogs.js),
#   user accounts, secrets, and a TracingOptions() instance.
```

`folder` is the single most important value: it is the root every aspect's `file` path
is resolved against. In the real driver it comes from `$react_html5_projectfolder`, so
the **same** definition project can be woven into a fresh checkout each build.

`tracingOptions` (an instance of `TracingOptions`, see `trackingOption.py`) is the
in-memory representation of the loaded `options/*.json`; aspect modules read its fields
to parameterise advice.

---

## 5.3 Actions (`actions.py`)

A class — `Html5AppAction` (and siblings `UWPAppAction`, `CastAppAction`,
`POCAppAction`) — whose `execute(extra)` dispatches on `self.job`:

```python
def execute(self, extra):
    if   self.job == 'auto_signin':     self.auto_signin_aspect()
    elif self.job == 'inject_logging':
        self.copyRemoteLogFolder()      # seed advisor library first
        self.logging_aspect()           # then weave
    elif self.job == 'performance':     self.performance_aspect()
    elif self.job == 'prebuild-tracing':
        self.afterProcess = "lint"      # post-process: run ESLint on touched files
        ...
    else:
        sys.exit(2)
```

Each `*_aspect()` method does the same three things:

```python
def logging_aspect(self):
    import html5App.aspects.logging                       # 1. import the definition module
    self.extraAspects = 'remoteLog'                       #    (opt) request import injection
    codeInjector.aspectRunners.runAspectIn(               # 2. hand its `aspects` to the engine
        html5App.aspects.logging.aspects,
        html5.config.folder,                              #    target folder from config
        self.onEachFile,                                  # 3. post-process hook
        self.context)
```

### The `onEachFile` hook

`runAspectIn` calls `onEachFile(aspect, file, content)` after each successful weave. The
real driver uses it for two cross-cutting follow-ups:

- **Import injection** — when `self.extraAspects == 'remoteLog'`, it calls
  `aspectHandlers.addRemoteLog(...)` so any file that now references `remoteLog` gets the
  import added.
- **Linting** — when `self.afterProcess == 'lint'`, it registers each touched `.js` file
  with an `ESLint` helper, run at the end via `executeESLint()` to auto-fix formatting
  of the injected code.

The demo's hook is a no-op (`return '', content`) — post-processing is optional.

### Copy-then-weave helpers

- `copyRemoteLogFolder()` → `fileutil.copyFolderIfEmpty(...)` seeds the advisor library,
  then runs `configure_remote_aspect()`.
- `copyStaticRemoteLogFile()` → `shutil.copyfile(...)` seeds `remoteLogs.js`, then weaves
  references to it.

---

## 5.4 Adding a new app

To target a new kind of project, mirror the `html5` package:

1. Create `myapp/config.py` with `name` and `folder` (where the target lives).
2. Create `myapp/actions.py` with a `MyAppAction` class whose `execute(extra)` maps jobs
   to `runAspectIn(...)` calls against your definition modules.
3. Register it in the entry point's `createAppAction(...)`:
   ```python
   elif app == 'myapp':
       return MyAppAction(self.job)
   ```
4. Put the engine and your definition project on `PYTHONPATH`, then run with
   `--app myapp --job <job>`.

## 5.5 Adding a new job to an existing app

1. Write/extend an aspect module in the definition project (e.g.
   `html5App/aspects/mytrace.py`).
2. Add a method on the actions class that imports it and calls `runAspectIn(...)`.
3. Add an `elif self.job == 'my-trace':` branch in `execute(...)`.
4. (Optional) add a shell wrapper — see [06-running.md](06-running.md).

Continue to **[06-running.md](06-running.md)**.
