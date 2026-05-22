# code-injector

`code-injector` is a small Python engine that **modifies the source files of another
project at build time** using the ideas of **Aspect-Oriented Programming (AOP)**.

Instead of editing the main project to add logging, instrumentation, environment
tweaks, or build fixes, you keep those modifications in a **separate project**. At
build time the injector weaves them into a _copy_ of the main project's source, builds
it, and leaves the main project's repository untouched. This gives you a clean
**separation of concerns**: the product code stays product code, and the
debug/instrumentation/build concerns live on their own.

```
┌─────────────────┐     reads      ┌──────────────────────┐    edits     ┌──────────────────┐  build  ┌──────────────────┐
│ Definition      │───────────────▶│  code-injector       │────────────▶ │  Main project    │ ──────▶ │  App bundle      │
│ project         │  aspects +     │  (engine)            │  in place    │  source files    │         │                  │
│                 │  advice code   │                      │              │  (before buil)   │         │                  │
└─────────────────┘                └──────────────────────┘              └──────────────────┘         └──────────────────┘
        ▲                                     ▲
        │   import path (PYTHONPATH)          │  build/deploy parameters
        └──────────────── Driver / app layer ─┘  (--app --job --env --branch --version)
```

## The three pieces

| Piece                  | Responsibility                                                                                                         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Engine**             | Generic. Knows how to find a _pointcut_ in a file and insert/replace/remove _advice_. Knows nothing about any project. |
| **Definition project** | Owns _what_ to inject and _where_: the **aspect dictionaries** and the code to inject (the "advisors").                |
| **Driver / app layer** | Owns _orchestration_: turns build/deploy parameters (env, branch, version, platform) into engine calls.                |

They are connected through environment variables like:

```bash
export PYTHONPATH=/.../code-injector:/..../inject-definition-project
```

## Read in this order

1. **[01-concepts.md](documentations/01-concepts.md)** — AOP vocabulary (aspect, pointcut, advice, join point) mapped onto this tool.
2. **[02-architecture.md](documentations/02-architecture.md)** — How the engine works internally, module by module.
3. **[03-aspect-reference.md](documentations/03-aspect-reference.md)** — The complete aspect-dictionary reference: every key and what it does.
4. **[04-defining-a-project.md](documentations/04-defining-a-project.md)** — How to build a definition project.
5. **[05-wiring-an-app.md](documentations/05-wiring-an-app.md)** — How the driver/app layer (`config.py`, `actions.py`, `index.py`) ties it together.
6. **[06-running.md](documentations/06-running.md)** — `PYTHONPATH`, the CLI, the shell drivers, and `options/*.json`.
7. **[07-walkthrough.md](documentations/07-walkthrough.md)** — A complete, runnable end-to-end example using the bundled `html5` sample.

## 30-second example

The bundled sample injects two `console.log` calls into `sampleCode/sample.js`:

```bash
cd /.../code-injector
python . --app html5 --job sample_job --branch main --version 1.0.0 --env dev
```

Target before:

```js
let a = 5
let b = 10
```

Target after:

```js
let a = 5
console.log('Assigned a to 5')
console.log('About to assign b to 10')
let b = 10
```

The _what_ (`console.log(...)`) and _where_ (`let a = 5;` / `let b = 10;`) come from
`html5/aspects/sampleJob.py`. The engine never had to know about this file.
