# 6. Running the injector

[← Back to index](../README.md)

## 6.1 PYTHONPATH — the glue

The engine and the definition project are separate trees. Both must be importable, so
put both roots on `PYTHONPATH`:

```bash
export PYTHONPATH=.../code-injector:.../defintiomn-project
```

This makes available:

- `codeInjector` (engine) and the demo `html5`/`uwp`/… app packages — from
  `code-injector/`;
- `html5App` (definition package: `html5App.aspects.logging`, etc.).

The driver imports definition modules by name (`import html5App.aspects.logging`), so if
`PYTHONPATH` is missing or wrong you get `ModuleNotFoundError`. This single variable is
what lets the _same_ engine drive _different_ definition projects.

## 6.2 Direct CLI invocation

### Bundled demo (self-contained)

```bash
cd .../code-injector
python . --app html5 --job sample_job --branch main --version 1.0.0 --env dev
```

`python .` runs `__main__.py`. Arguments:

| Arg                                | Meaning                                     |
| ---------------------------------- | ------------------------------------------- |
| `--app`                            | Which app package to dispatch to (`html5`). |
| `--job`                            | Which job within that app (`sample_job`).   |
| `--branch` / `--version` / `--env` | Build context used for aspect conditions.   |

### Real driver (with options/extra)

```bash
python .../aspects/pythons/index.py \
  --app=html5 \
  --job=inject_logging \
  --env=perf \
  --branch=acn_develop \
  --version=14.2.0 \
  --options=freeview \
  --extra=
```

Extra arguments:

| Arg         | Meaning                                                                         |
| ----------- | ------------------------------------------------------------------------------- |
| `--options` | Name of an `options/<name>.json` file selecting a platform profile (see below). |
| `--extra`   | Free-form extra flag passed to the action's `execute(extra)`.                   |

## 6.3 options/\*.json — per-platform profiles

`aspects/pythons/html5/options/` holds one folder/file per platform (`freeview`,
`tizen`, `ps4`, `ps5`, `amazon`, `xbox`, `youview`, `virgin`, …). Example:

```json
{
  "platform": "freeview",
  "context": { "versionSuffix": "" },
  "logging": {
    "enabled": true,
    "request": "true",
    "player": "true",
    "storage": "false",
    "performance": "true",
    "observable": "false",
    "org": "true"
  },
  "usePlusUser": false,
  "httpVideo": "tests",
  "platformDebug": "freeview_poc"
}
```

When `--options=freeview` is passed, the driver:

1. loads the JSON and populates `TracingOptions` (`html5/trackingOption.py`), whose
   fields aspect modules read to **parameterise advice** (e.g. the `logging.*` flags are
   `.format()`-substituted into `remote-log/config.js`);
2. if `context.versionSuffix` is set, appends it to the build version (or replaces it
   when prefixed with `REPLACE:`).

So one job behaves differently per platform without changing any aspect code — the JSON
toggles features and supplies values.

## 6.4 The shell drivers

In the production setup the Python entry point is wrapped by shell functions under
`.../aspects/`:

- `index.sh` sources `html5.sh`, `uwp.sh`, `cast.sh`, `poc.sh`, `deployment.sh`.
- `html5.sh` defines `aspect_html5_inject_to_code`, the common wrapper:

  ```bash
  aspect_html5_inject_to_code() {
      pythonresponseoutput=$($pythonCommandPath $aspectCorePythonScriptPath/index.py --app=html5 \
        --job=$1 \
        --env=$remoteLogEnv \
        --branch=$currentHtmlBranchName \
        --options=$2 \
        --extra=$3 \
        --version=$html5DeployedVersion 2>&1)

      if [[ $pythonresponseoutput == "" ]]; then
          echo "aspect successful in $react_html5_projectfolder"
      else
          # ANY output is treated as failure → abort the deploy
          onDeploymentJobFailed $3
          exit 1
      fi
  }
  ```

  with thin job wrappers on top: `aspect_html5_logging`, `aspect_html5_performance`,
  `aspect_html5_auto_signin`, `aspect_html5_http_request`, `aspect_html5_watchlive`,
  `aspect_html5_prebuild_performance`, etc.

### Environment variables the shell layer expects

| Variable                     | Used for                                                 |
| ---------------------------- | -------------------------------------------------------- |
| `BINROOTDIR`                 | Locating the `aspects/*.sh` scripts.                     |
| `pythonCommandPath`          | The Python interpreter to run.                           |
| `aspectCorePythonScriptPath` | Path to `pythons/` (where `index.py` lives).             |
| `react_html5_projectfolder`  | The **target** project folder (becomes `config.folder`). |
| `remoteLogEnv`               | Maps to `--env`.                                         |
| `currentHtmlBranchName`      | Maps to `--branch`.                                      |
| `html5DeployedVersion`       | Maps to `--version`.                                     |

> **Success = silence.** The shell wrapper treats _any_ stdout/stderr as failure. That
> is why the engine prints only on error and otherwise stays quiet — a successful
> injection produces no output, and the wrapper prints its own "successful" line.

## 6.5 Where this fits in a build

Typical order during a deploy:

1. Check out the main project into `$react_html5_projectfolder`.
2. Export `PYTHONPATH` (engine + definition project).
3. Run the relevant `aspect_html5_*` shell functions (or `index.py` directly) to weave
   in the required concerns for the target `--env`/`--branch`/`--options`.
4. Build the now-modified target project as normal.

The main project's own repository is never modified — only the checked-out working copy
that gets built.

Continue to **[07-walkthrough.md](07-walkthrough.md)**.
