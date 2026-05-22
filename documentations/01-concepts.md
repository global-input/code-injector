# 1. Concepts — AOP applied to source files

[← Back to index](../README.md)

## Why AOP?

Some concerns cut _across_ a whole codebase: logging, tracing, performance
instrumentation, environment-specific tweaks, temporary build fixes. If you edit the
main project to add them, you mix product code with throwaway/debug code, and you have
to carefully unpick it later. **Aspect-Oriented Programming** keeps those
**cross-cutting concerns** in their own modules ("aspects") and **weaves** them into
the target only when needed.

This tool applies that idea at the **source-text / build-time** level. It does not run
inside your program; it edits files on disk before your normal build runs. Think of it
as a programmable, condition-aware "find and insert/replace" that is organised the way
AOP frameworks are organised.

## Vocabulary, mapped to this tool

| AOP term       | Meaning here                                                                                              | Where it lives                              |
| -------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Join point** | A location in a source file where you _could_ weave code (a line of code, a function call).               | The target project's files.                 |
| **Pointcut**   | The text/pattern that selects join points.                                                                | The `pointcut` key of an aspect.            |
| **Advice**     | The code to weave in, and _where_ relative to the join point (before / after / replace / remove).         | The `advice` + `position` keys.             |
| **Aspect**     | One pointcut+advice rule (plus conditions) for one file.                                                  | A dict inside the `aspects` list.           |
| **Weaving**    | The act of applying advice at the matched join points.                                                    | `codeInjector.aspectHandlers.handleAspect`. |
| **Advisor**    | (Project-specific term in the aspect project) the actual library/snippet code that the advice calls into. | aspect definition project                   |

## The aspect dictionary — the contract

Everything centres on one Python data shape. A definition file exposes a list called
`aspects`:

```python
aspects = [
    {
        "file": "src/helpers/log.js",      # target file (relative to the project folder)
        "aspects": [                          # one or more rules for THIS file
            {
                "pointcut": "proxy(",         # the join point: text to find
                "advice":  "remoteLog.onAppProxyLogs(proxy, ",   # what to weave
                "position": "replace"         # how to weave it (before/after/replace/remove)
            }
        ]
    },
]
```

Read it as: _"In `src/helpers/log.js`, find `proxy(` and replace it with
`remoteLog.onAppProxyLogs(proxy, `."_ The engine consumes exactly this shape — see
[03-aspect-reference.md](03-aspect-reference.md) for every supported key.

## Build context: env / branch / version

Each run carries a small **context** — `env`, `branch`, `version` — describing the
build. Aspects can be made conditional on it (e.g. only inject auto-sign-in on
`dev`/`perf`/`test`, never on `prod`). The context is created from CLI arguments and
stored per "app" (see [02-architecture.md](02-architecture.md#contextpy)).

## Two ways to express advice

1. **External aspect dictionaries** (the normal way) — Python files listing
   `{file, aspects:[…]}`. Covered throughout this guide.
2. **Inline `@aspect` annotations** — special comments left _inside the target source_
   that the engine "activates" by stripping the comment markers. Useful when the code
   to inject is large and you'd rather keep it next to the code it modifies. Covered in
   [03-aspect-reference.md](03-aspect-reference.md#inline-aspect-annotations).

## What weaving operates on

The engine is **text-based**, not AST-based. A pointcut is matched as literal text
(`exact`), a regular expression (`regex`), or a function call whose arguments are
copied (`function`). This keeps the engine language-agnostic — it has been used on
JavaScript/JSX, but nothing ties it to a particular language.

Continue to **[02-architecture.md](02-architecture.md)**.
