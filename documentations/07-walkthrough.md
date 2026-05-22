# 7. End-to-end walkthrough (the bundled sample)

[← Back to index](../README.md)

This walks through the self-contained demo shipped with the engine. It needs no
definition project — the aspects live in `html5/aspects/sampleJob.py`. The commands and
output below were run and verified.

## The pieces involved

```
code-injector/
├── __main__.py                 # entry point (python . dispatches here)
├── html5/
│   ├── config.py               # name='html5', folder='./sampleCode'
│   ├── actions.py              # Html5AppAction: job 'sample_job' → runAspectIn(...)
│   └── aspects/sampleJob.py    # the aspect definitions
└── sampleCode/sample.js        # the target file
```

`html5/config.py`:

```python
name   = 'html5'
folder = "./sampleCode"
```

`html5/aspects/sampleJob.py` (trimmed):

```python
aspects = [
  { "file": "sample.js",
    "aspects": [
      { "pointcut": "let a = 5;",
        "advice":  "console.log('Assigned a to 5')",
        "position": "after" },
      { "pointcut": "let b = 10;",
        "advice":  "console.log('About to assign b to 10')",
        "position": "before" },
    ]
  },
]
```

`html5/actions.py` maps the job to an engine run:

```python
def __sample_job_aspect(self):
    import html5.aspects.sampleJob
    codeInjector.aspectRunners.runAspectIn(
        html5.aspects.sampleJob.aspects, html5.config.folder, self.__on_each_file, self.context)

def execute(self):
    if self.job == 'sample_job':
        self.__sample_job_aspect()
```

## Run it

```bash
cd .../code-injector
export PYTHONPATH=.../code-injector
python3 . --app html5 --job sample_job --branch main --version 1.0.0 --env dev
```

The process exits `0` and **prints nothing** on success (recall: success = silence).

## Target before

```js
// This code will be modified as configured in html5/aspects/sampleJob.py

let a = 5
let b = 10
```

## Target after

```js
// This code will be modified as configured in html5/aspects/sampleJob.py

let a = 5
console.log('Assigned a to 5')
console.log('About to assign b to 10')
let b = 10
```

Note how each injected line lands on its **own** line — `ContentRange.getSeparators`
inserted the needed `\n` without adding blank-line noise.

## What happened, step by step

1. `__main__.py` parsed the args and called `context.createApp('html5', 'main', '1.0.0', 'dev')`.
2. `Html5AppAction('sample_job').execute()` dispatched to `__sample_job_aspect()`.
3. That imported `html5.aspects.sampleJob` and called `runAspectIn(aspects, './sampleCode', onEachFile, context)`.
4. The engine resolved `./sampleCode/sample.js`, read it, and for each inner aspect:
   - `checkAspectCondition` passed (no conditions, advice not yet present);
   - `handleAspect` found the pointcut and inserted the advice (`after` `let a = 5;`,
     `before` `let b = 10;`).
5. The file was written back.

## Idempotency check

Run the **same command again**. Because `skip-if-advice-found` defaults to `True`, the
engine sees its own `console.log(...)` advice already present and skips both aspects —
the file is unchanged, no duplicate logs. (To prove it to yourself, run twice and diff.)

## Restoring the sample

The demo edits the file in place. To get the original back:

```bash
cd .../code-injector
git checkout -- sampleCode/sample.js
```

(In a real build the target is a throwaway checkout, so in-place editing is fine and
the source repo is never touched — see [06-running.md](06-running.md#65-where-this-fits-in-a-build).)

## From demo to real use

| Demo                                                | Real                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------- |
| Aspects in `html5/aspects/sampleJob.py` (same repo) | Aspects in `.../html5App/aspects/*.py` (separate project)           |
| `folder = "./sampleCode"`                           | `folder = os.environ['react_html5_projectfolder']` (build checkout) |
| One job `sample_job`                                | Many jobs: `inject_logging`, `performance`, `auto_signin`, …        |
| No-op `onEachFile`                                  | Lint + `remoteLog` import injection                                 |
| `python .` by hand                                  | `aspect_html5_*` shell functions inside the deploy pipeline         |

You now have the full picture: the [engine](02-architecture.md) is generic, the
[definition project](04-defining-a-project.md) supplies the rules and payload, and the
[driver](05-wiring-an-app.md) orchestrates them per [build context and
platform](06-running.md).
