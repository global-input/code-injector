# 3. Aspect dictionary reference

[← Back to index](../README.md)

This is the complete reference for the data shape the engine consumes. An aspect
definition module exposes a Python list named `aspects`:

```python
aspects = [
    {
        "file": "<path relative to the target project folder>",
        # group-level conditions may also go here (env, branch, ...)
        "aspects": [
            { "pointcut": ..., "advice": ..., "position": ..., ... },
            ...
        ]
    },
    ...
]
```

There are **two condition layers**:

- **Group level** (the outer dict, alongside `file`) — checked once, before the file is
  read. Use it to skip an entire file for an env/branch, or when the file may not
  exist.
- **Aspect level** (each inner dict) — checked with the file content available, so it
  can also test `skip-if-found` / `skip-if-not-found`.

---

## Targeting keys

| Key             | Type                             | Default                    | Meaning                                                                                                                               |
| --------------- | -------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `file`          | string                           | — (required, group level)  | Target file, relative to the project folder configured in `config.py`.                                                                |
| `pointcut`      | string \| list \| `'@aspect'`    | — (required, aspect level) | Text/pattern selecting the join point(s). A list is tried in order until one matches. `'@aspect'` switches to inline-annotation mode. |
| `match-type`    | `exact` \| `regex` \| `function` | `exact`                    | How `pointcut` is matched. `regex` uses `re.search`; `function` enables argument copying.                                             |
| `trim-pointcut` | bool                             | `True`                     | Strip surrounding whitespace from `pointcut` (so you can use indented triple-quoted strings).                                         |

## Advice keys

| Key           | Type                                         | Default  | Meaning                                                                                                                                      |
| ------------- | -------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `advice`      | string \| `{before, after}`                  | —        | Code to weave. A dict wraps the match (`before` in front, `after` behind); either side may be omitted. Not required when `position: remove`. |
| `position`    | `before` \| `after` \| `replace` \| `remove` | `before` | Where the advice goes relative to the match.                                                                                                 |
| `trim-advice` | bool                                         | `True`   | Strip surrounding whitespace from advice text.                                                                                               |

## Condition keys

| Key                      | Type           | Level  | Meaning                                                                                                                                             |
| ------------------------ | -------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disabled`               | bool           | both   | `True` → never run this aspect.                                                                                                                     |
| `env`                    | string \| list | both   | Run only when `context.env` matches.                                                                                                                |
| `branch`                 | string \| list | both   | Run only when `context.branch` matches.                                                                                                             |
| `branch-to-skip`         | string \| list | both   | Skip when `context.branch` matches.                                                                                                                 |
| `skip-if-file-not-found` | bool           | both   | Skip if the target file is missing (instead of erroring).                                                                                           |
| `skip-if-not-found`      | string \| list | aspect | Run only if the text(s) are present in the file. List ⇒ _all_ required.                                                                             |
| `skip-if-found`          | string \| list | aspect | Skip if the text(s) are present. List ⇒ _any_ match skips.                                                                                          |
| `skip-if-advice-found`   | bool           | aspect | Default `True`. When `skip-if-found` is absent, the advice text itself is used as the "already injected?" check. Set `False` to allow re-injection. |
| `optional`               | bool           | aspect | `True` → if the pointcut is never found, succeed silently (no error).                                                                               |

> **Idempotency:** because `skip-if-advice-found` defaults to `True`, re-running the
> injector does not double-apply advice. If you _intend_ to inject the same text in
> several places, give each its own distinct advice or set `skip-if-found` explicitly.

---

## Examples

### Replace a call to wrap it

```python
{
  "file": "src/helpers/log.js",
  "aspects": [{
      "pointcut": "proxy(",
      "advice":  "remoteLog.onAppProxyLogs(proxy, ",
      "position": "replace"
  }]
}
```

Turns `proxy(...)` into `remoteLog.onAppProxyLogs(proxy, ...)`.

### Insert after a marker, with parameters from build options

```python
{
  "file": "remote-log/config.js",
  "aspects": [{
      "pointcut": "const initConfig = ()=>{",
      "advice": '''
          logs.request = {request};
          logs.player = {player};
      '''.format(request=html5.config.tracingOptions.logging.request.value,
                 player=html5.config.tracingOptions.logging.player.value),
      "position": "after"
  }]
}
```

The advice is a normal Python string, so values from the loaded `options/*.json`
(surfaced through `tracingOptions`) can be substituted with `.format(...)`.

### Restrict to non-production environments

```python
{
  "file": "src/components/RegAndSignInFlow/RegAndSignInFlow.js",
  "env": ["dev", "perf", "test"],          # group-level condition
  "aspects": [
      {"pointcut": "setEmailInput(",
       "advice":  "remoteLog.onSetEmailInput(setEmailInput, ",
       "position": "replace"},
      {"pointcut": "setPasswordInput(",
       "advice":  "remoteLog.onSetPasswordInput(setPasswordInput, ",
       "position": "replace"},
  ]
}
```

### Optional replace that tolerates a missing pointcut

```python
{
  "file": "src/components/ErrorBoundary/ErrorBoundary.js",
  "aspects": [{
      "pointcut": "static getDerivedStateFromError() {",
      "advice":  "static getDerivedStateFromError(error) {\n  log.error('[ErrorBoundary] ' + error);",
      "position": "replace",
      "optional": True          # don't fail the build if the signature changed
  }]
}
```

### Wrap a function call, copying its real arguments (`match-type: function`)

```python
{
  "file": "src/player/index.js",
  "aspects": [{
      "pointcut": "createPlayer(",
      "advice":  "traceCreatePlayer(",
      "match-type": "function",
      "position": "replace"
  }]
}
```

If the file contains `createPlayer(a, b, opts)`, the engine copies the argument list so
the result is `traceCreatePlayer(a, b, opts)` — without you naming the arguments.

---

## Inline `@aspect` annotations

Sometimes the advice is large and lives best beside the code it modifies. Park it
inside the **target file** as a commented annotation:

```js
function start() {
  /* @aspect'''
  remoteLog.trace('start() entered');
  remoteLog.attachTimings(performanceMonitor);
  ''' */
}
```

Then a single aspect activates _all_ such annotations in the file:

```python
{
  "file": "src/app/start.js",
  "aspects": [{ "pointcut": "@aspect" }]
}
```

The engine strips the comment markers and the `@aspect'''…'''` wrapper, leaving the
inner lines as live code. (See `handleAnnotatedAspect` in
[02-architecture.md](02-architecture.md#handleannotatedaspect-pointcut--aspect).)

---

## Composing multiple aspect lists in one file

A definition module can build its `aspects` list from several blocks — handy for
grouping related rules:

```python
aspects = [ ... core rules ... ]

errorBoundary = [ { "file": ..., "aspects": [ ... ] } ]

aspects.extend(errorBoundary)
```

Continue to **[04-defining-a-project.md](04-defining-a-project.md)**.
