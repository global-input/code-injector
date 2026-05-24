# code-injector

## Table of Contents

- [Start Here: A Build Story](#start-here-a-build-story)
- [What code-injector is](#what-code-injector-is)
- [The three pieces](#the-three-pieces)
- [30-second example](#30-second-example)
- [Concepts: AOP Applied to Source Files](#concepts-aop-applied-to-source-files)
- [Engine Architecture](#engine-architecture)
- [Aspect Dictionary Reference](#aspect-dictionary-reference)
- [Building a Definition Project](#building-a-definition-project)
- [Wiring an App / Driver Layer](#wiring-an-app--driver-layer)
- [Running the Injector](#running-the-injector)
- [End-to-End Walkthrough](#end-to-end-walkthrough)
- [Tiny Boot Lab](#tiny-boot-lab)

## Start Here: A Build Story

You have a TV app, console access is painful, and the bug only happens on the device.
You want one extra line in the app:

```js
console.log('[device] boot reached')
```

But you do not want that line committed to the product repo. You want it only in the
temporary checkout that the build system is about to package.

That is the feeling this project is built around.

`code-injector` lets a separate project say: open this file, find this small piece of
text, and put this other piece of text there. It does that before the normal app build.
The app source stays clean. The throwaway build copy gets the debug behavior.

The rest of this tutorial keeps that one idea alive and slowly makes it more useful.

### First Win: Prove the App Reached Boot

Start with a tiny app file:

```js
function boot() {
  startApp()
}

function startApp() {
  renderHome()
}

function renderHome() {
  console.log('home rendered')
}

boot()
```

The need is small and familiar:

> When this build runs on a device, I want to know whether `boot()` was reached.

The definition is also small:

```python
aspects = [
    {
        "file": "src/app.js",
        "aspects": [
            {
                "pointcut": "function boot() {",
                "advice": "  console.log('[device] boot reached');",
                "position": "after",
                "trim-advice": False
            }
        ]
    }
]
```

After the injector runs, the build copy becomes:

```js
function boot() {
  console.log('[device] boot reached')
  startApp()
}

function startApp() {
  renderHome()
}

function renderHome() {
  console.log('home rendered')
}

boot()
```

That is the whole project in one breath. A rule lives outside the app. The rule touches
the app only when the build asks for it.

You can run this first win:

```bash
cd /Users/user/workspace/utils/code-injector/lab
./scripts/reset.sh
./scripts/run.sh
sed -n '1,120p' app/src/app.js
```

Run `./scripts/run.sh` again. The log line will not be duplicated. The injector notices
that the advice is already present and skips it.

### The First Real Trick: Make Typing on a TV Remote Disappear

On a device, signing in with a remote control is slow. A debug build should fill the
email and password for you. The real project already does this in:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/autosignin.py`

The target code has calls like this:

```js
setEmailInput(value)
setPasswordInput(value)
```

The aspect changes the function being called:

```python
aspects=[
  {
      "file": "src/components/RegAndSignInFlow/RegAndSignInFlow.js",
       "env":["dev","perf", "test"],
       "aspects":[{
            "pointcut":'''
                    setEmailInput(
            ''',
            "advice":'''
                    remoteLog.onSetEmailInput(setEmailInput,
            ''',
            "position": "replace"
        },{
            "pointcut":'''
                    setPasswordInput(
            ''',
            "advice":'''
                    remoteLog.onSetPasswordInput(setPasswordInput,
            ''',
            "position": "replace"
        }]
  }
]
```

Now the call becomes:

```js
remoteLog.onSetEmailInput(setEmailInput, value)
remoteLog.onSetPasswordInput(setPasswordInput, value)
```

The interesting part is not just the replacement. It is the line that says:

```python
"env":["dev","perf", "test"]
```

That is the safety catch. The auto sign-in behavior belongs in useful debug builds,
not production builds.

### The Moment It Becomes a Product: Give the Debug Library a Config

Once you inject more than one line, you need a small library behind those lines. In
this project that library is `remote-log`. The injected code calls it. The library does
the heavier work.

But a copied debug library needs to know which build it is inside and where to send
logs. The real project handles that in:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/remoteConfig.py`

The target file has a placeholder:

```js
const version = '100.100.100'
const host = 'ps5.mycompany.com'

export default {
  remoteLogHostURL: `${protocol}://${host}/remote-logs`,
  performanceURL: `${protocol}://${host}/performance/action`
}
```

The aspect uses the build context and the selected environment:

```python
import codeInjector.context

context=codeInjector.context.getAppContext('html5')

aspects=[
  {
      "file": "remote-log/config.js",
        "aspects":[{
            "pointcut":'''
                    100.100.100
            ''',
            "advice":'''
                {version}
            '''.format(version=context.version),
            "position": "replace"
        },{
            "pointcut":'''
                    remoteLogHostURL:`${protocol}://${host}/remote-logs`,
            ''',
            "advice":'''
                    remoteLogHostURL:`${protocol}://${host}/debug-local/remote-logs`,
            ''',
            "position": "replace",
            "env":['dev','test']
        },{
            "pointcut":'''
                    performanceURL:`${protocol}://${host}/performance/action`,
            ''',
            "advice":'''
                    performanceURL:`${protocol}://${host}/debug-local/performance/action`,
            ''',
            "position": "replace",
            "env":['dev','test']
        }]
  }
]
```

A build launched with version `14.2.0-device-debug` leaves the copied library with:

```js
const version = '14.2.0-device-debug'
const host = 'ps5.mycompany.com'

export default {
  remoteLogHostURL: `${protocol}://${host}/debug-local/remote-logs`,
  performanceURL: `${protocol}://${host}/debug-local/performance/action`
}
```

The build now has an identity. The logs arriving on the server can tell you exactly
which package produced them.

### Turn Existing Logs Into Remote Logs

The app already logs. The problem is that the logs are trapped on the device. The real
`logging.py` aspect changes the logging helper instead of chasing every log call.

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/logging.py`

The app has a helper that calls:

```js
proxy('player', message)
```

The aspect replaces the beginning of that call:

```python
{
    "file": "src/helpers/log.js",
    "aspects":[{
        "pointcut":'''
                proxy(
        ''',
        "advice":'''
                remoteLog.onProxyLogs(proxy,
        ''',
        "position": "replace"
    }]
}
```

The build copy now calls:

```js
remoteLog.onProxyLogs(proxy, 'player', message)
```

The original logger still exists. The debug library sits in front of it, records what
it needs, then lets normal logging continue.

The same aspect file also configures which log families are enabled:

```python
"advice":'''
        logs.request = {request};
        logs.player = {player};
        logs.storage = {storage};
        logs.performance = {performance};
        logs.observable = {observable};
        logs.t4.enabled ={t4_enabled};
'''.format(
    request=html5.config.tracingOptions.logging.request.value,
    player=html5.config.tracingOptions.logging.player.value,
    storage=html5.config.tracingOptions.logging.storage.value,
    performance=html5.config.tracingOptions.logging.performance.value,
    observable=html5.config.tracingOptions.logging.observable.value,
    t4_enabled=html5.config.tracingOptions.logging.t4.value)
```

That is when aspects become more than search-and-replace. They become a way to turn a
build profile into code.

### Follow a Request From Start to Failure

When a device says "something failed," the next question is usually: which request?
Which URL? Did the response arrive? Did the exception happen before or after the
response?

The real project answers that in:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/httpRequest.py`

The target helper contains familiar pieces:

```js
return Promise.race(promiseArray)
  .then(async res => {
    return res
  })
  .catch(async err => {
    throw err
  })

export default makeRequest
```

The aspect adds a start time before the request race:

```python
{
    "pointcut":'''
    return Promise.race(promiseArray)
    ''',
    "advice":'''
    const requestStartTimeForRemoteLog = Date.now();

    ''',
    "position": "before"
}
```

It records the response:

```python
{
    "pointcut":'''
            .then(async res => {
    ''',
    "advice":'''
            remoteLog.onHttpResponseReceived(url, res, requestStartTimeForRemoteLog);
    ''',
    "position": "after"
}
```

It records the exception:

```python
{
    "pointcut":'''
            .catch(async err => {
    ''',
    "advice":'''
            remoteLog.onErrorException('makeRequest',err,[url]);
            remoteLog.remoteLog.error(err+" while making requesting to: "+url);
    ''',
    "position": "after"
}
```

And at the end it wraps the exported function:

```python
{
    "pointcut":'''
            export default makeRequest;
    ''',
    "advice":'''
            const remoteMakeRequest = inputParam => remoteLog.onMakeRequest(makeRequest, inputParam);
export default remoteMakeRequest;
    ''',
    "position": "replace"
}
```

The final build copy has a request story: when it started, what response came back,
and what error happened if it failed.

### Redirect Hard-Coded Vendor Hosts Without Touching Vendor Code

Vendor files often contain a real production endpoint. For device debugging, you may
need those calls to go somewhere else.

The Adobe example is exactly that:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/adobe/changeAdobeTargetHost.py`

The target files contain:

```js
const primaryAdobeHost = 'analytics.mycompany.com'
const fallbackAdobeHost = 'analytic2.mycompany.com'
```

The aspect takes the replacement host from the active tracing options:

```python
import html5.config
aspects=[{
      "file": "src/services/tracking/adobeAnalytics/adobeAnalyticsHelpers.js",
        "aspects":[{
            "pointcut":'''
                   analytics.mycompany.com
            ''',
            "advice":'''
                   {adobeTargetHost}
            '''.format(adobeTargetHost=html5.config.tracingOptions.adobeTargetHost.value),
            "position": "replace"
          },{
            "pointcut":'''
                   analytic2.mycompany.com
            ''',
            "advice":'''
                   {adobeTargetHost}
            '''.format(adobeTargetHost=html5.config.tracingOptions.adobeTargetHost.value),
            "position": "replace"
          }]
       },{
           "file": "src/static/lib/appmeasurement/VisitorAPI.js",
            "aspects":[{
               "pointcut":'''
                   analytics.mycompany.com
              ''',
              "advice":'''
                   {adobeTargetHost}
               '''.format(adobeTargetHost=html5.config.tracingOptions.adobeTargetHost.value),
            "position": "replace"
        },{
               "pointcut":'''
                   analytic2.mycompany.com
              ''',
              "advice":'''
                   {adobeTargetHost}
               '''.format(adobeTargetHost=html5.config.tracingOptions.adobeTargetHost.value),
            "position": "replace"
        }]
  }
]
```

If the option says:

```python
html5.config.tracingOptions.adobeTargetHost.value == "adobe-debug.example.local"
```

the build copy becomes:

```js
const primaryAdobeHost = 'adobe-debug.example.local'
const fallbackAdobeHost = 'adobe-debug.example.local'
```

The Iterative aspect does the same kind of thing for `iterative.net`:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/iterative/changeIterativeDomain.py`

That is a clean pattern: hard-coded vendor value in source, build-profile value in the
definition project, replaced only for the build that asked for it.

### Make Branch Differences Boring

Real products have branches where the same intent is written a little differently.
The Tizen widget name aspect handles that without duplicating the whole job:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/changeWgtFileName.py`

One branch says:

```xml
<name xml:lang="en-gb">Media APP</name>
```

Another says:

```xml
<name xml:lang="en-gb">TV Application</name>
```

The aspect accepts either:

```python
"pointcut":['''
         <name xml:lang="en-gb">Media APP</name>
''','''
         <name xml:lang="en-gb">TV Application</name>
'''],
"advice":'''
          <name>{wgtFileName}</name>
           <name xml:lang="en-gb">TV Application</name>
'''.format(wgtFileName=html5.config.tracingOptions.tizenWgtFileName.value),
"position": "replace",
"skip-if-found":"<name>{wgtFileName}</name>".format(
    wgtFileName=html5.config.tracingOptions.tizenWgtFileName.value)
```

The `skip-if-found` line matters. If the widget name is already there, the aspect backs
away. That keeps repeated runs calm.

### Measure Performance Without Rebuilding the App by Hand

Performance work usually starts with a rough question:

> Where did the launch time go?

The real `performance.py` aspect answers by placing markers at important moments.

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/performance.py`

It starts the clock in HTML:

```python
{
    "file": "src/static/index.html",
    "aspects":[{
        "pointcut":'''
                <head>
        ''',
        "advice":'''
                <script type="text/javascript">window.dilshatStartTime=new Date();</script>
        ''',
        "position": "after"
    }]
}
```

It records that the app shell mounted:

```python
{
    "file": "src/client/AppShell.js",
    "aspects":[{
        "pointcut":'''
                importAndLoadXdk();
        ''',
        "advice":'''
                remoteLog.performance.onAppShellMounted();
        '''
    }]
}
```

It records app configuration after a tracking launch call, even if the exact arguments
change:

```python
{
    "pointcut":'''
        tracking\.launch\(.*\);
    ''',
    "advice":'''
        remoteLog.performance.onAppConfigured();
    ''',
    "match-type":"regex",
    "position": "after"
}
```

It handles branch-specific Home page code:

```python
{
    "pointcut":'''
        useRegisterFocusable(pageId);
    ''',
    "advice":'''
        remoteLog.performance.useHomePerformance(undefined,items,homeResponse?.isFetching);
    ''',
    "position": "after",
    "branch-to-skip":"performance/JIRA-6143-poc"
},{
    "pointcut":'''
        useRegisterFocusable(pageId);
    ''',
    "advice":'''
        remoteLog.performance.useHomePerformance(undefined,homeData && homeData.slices,(!dataReady && heroReady));
    ''',
    "position": "after",
    "branch":"performance/JIRA-6143-poc"
}
```

It also protects optional platform files:

```python
{
    "file": "src/components/player/Player/YouviewPlayer.js",
    "skip-if-file-not-found":True,
    "aspects":  [{
        "pointcut":'''
           environment.addEventListener(environment.MEDIA.TIME_UPDATE, onTimeUpdate);
        ''',
        "advice":'''
            environment.addEventListener(environment.MEDIA.TIME_UPDATE, remoteLog.performance.onMediaTimerUpdate);
        ''',
        "position":"before"
    }]
}
```

This is where the injector starts to feel like a build instrument panel. One job can
touch HTML, React views, player code, branch variants, and optional platform files.

### When the Build Itself Needs a Small Rescue

Sometimes the problem is not runtime observability. Sometimes the checkout cannot even
build with the current toolchain.

The real build-fix aspect lives here:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/fixes/fix_build_error.py`

It bumps package versions:

```python
{
    "file": "package.json",
    "aspects":[{
        "pointcut":'''
               "node-sass": "^4.14.1",
        ''',
        "advice":'''
               "node-sass": "^6.0.1",
        ''',
       "position": "replace"
    },{
        "pointcut":'''
                "sass-loader": "^9.0.3",
        ''',
        "advice":'''
            "sass-loader": "^10.1.1",
        ''',
        "position": "replace"
    }]
}
```

### When the Payload Is Too Big, Keep It Beside the Aspect

Some build-time additions are too large to write inside a Python string. The automation
and memory-report tools solve that by reading HTML, CSS, or JS files from beside the
aspect.

From:

`/Users/user/workspace/utils/remote-log-adapter/html5App/aspects/tool/my4autoplay.py`

```python
script_dir = os.path.dirname(os.path.abspath(__file__))

def get_file_content(directory, filename):
    file_path = os.path.join(directory, filename)
    with open(file_path, 'r') as file:
        return file.read()

def get_script_file(directory, filename):
    return get_file_content(os.path.join(script_dir, directory), filename)

html_content = get_script_file( 'html', 'my4autoplay.html')
css_content = get_script_file('css', 'overlay.css')
```

Then the aspect injects those files into `index.html`:

```python
automationNotification=[{
    "file":"src/static/index.html",
    "aspects":[{
        "pointcut":'''</style>''',
        "advice":'''
            {cssContent}
        '''.format(cssContent=css_content),
        "position": "before"
    },{
        "pointcut":'''</body>''',
        "advice":'''
            {htmlContent}
        '''.format(htmlContent=html_content),
        "position": "before"
    }]
}]
```

That is a good rule of thumb: keep the aspect as the wiring, and keep large payloads as
real files.

### The Pattern to Remember

The tutorial started with one line after `boot()`. The real project uses the same move
for bigger needs:

```text
Need: I cannot see what the device is doing.
Move: Insert a tiny hook that calls remote-log.

Need: I cannot type credentials on a TV remote.
Move: Replace input setters with auto sign-in wrappers, but only for dev/perf/test.

Need: The vendor endpoint must change for this build.
Move: Replace literal hosts with values from the selected options profile.

Need: A branch changed the code shape.
Move: Give the aspect more than one acceptable needle, or gate by branch.

Need: The platform file is not present in every checkout.
Move: Skip that file when it is missing.

Need: The build pipeline needs a temporary fix.
Move: Patch the disposable checkout, not the product source.
```

If you keep that pattern in your head, the aspect files stop looking like a bag of
dictionary keys. They become build stories: here is the pain, here is the tiny hook,
here is the copied build doing the job.

## What code-injector is

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
│                 │  advice code   │                      │              │  (before build)   │         │                  │
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

## Concepts: AOP Applied to Source Files

### Why AOP?

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

### Vocabulary, mapped to this tool

| AOP term       | Meaning here                                                                                              | Where it lives                              |
| -------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Join point** | A location in a source file where you _could_ weave code (a line of code, a function call).               | The target project's files.                 |
| **Pointcut**   | The text/pattern that selects join points.                                                                | The `pointcut` key of an aspect.            |
| **Advice**     | The code to weave in, and _where_ relative to the join point (before / after / replace / remove).         | The `advice` + `position` keys.             |
| **Aspect**     | One pointcut+advice rule (plus conditions) for one file.                                                  | A dict inside the `aspects` list.           |
| **Weaving**    | The act of applying advice at the matched join points.                                                    | `codeInjector.aspectHandlers.handleAspect`. |
| **Advisor**    | (Project-specific term in the aspect project) the actual library/snippet code that the advice calls into. | aspect definition project                   |

### The aspect dictionary — the contract

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
[Aspect Dictionary Reference](#aspect-dictionary-reference) for every supported key.

### Build context: env / branch / version

Each run carries a small **context** — `env`, `branch`, `version` — describing the
build. Aspects can be made conditional on it (e.g. only inject auto-sign-in on
`dev`/`perf`/`test`, never on `prod`). The context is created from CLI arguments and
stored per "app" (see [context.py](#contextpy)).

### Two ways to express advice

1. **External aspect dictionaries** (the normal way) — Python files listing
   `{file, aspects:[…]}`. Covered throughout this guide.
2. **Inline `@aspect` annotations** — special comments left _inside the target source_
   that the engine "activates" by stripping the comment markers. Useful when the code
   to inject is large and you'd rather keep it next to the code it modifies. Covered in
   [Inline `@aspect` annotations](#inline-aspect-annotations).

### What weaving operates on

The engine is **text-based**, not AST-based. A pointcut is matched as literal text
(`exact`), a regular expression (`regex`), or a function call whose arguments are
copied (`function`). This keeps the engine language-agnostic — it has been used on
JavaScript/JSX, but nothing ties it to a particular language.

## Engine Architecture

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

### context.py

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
    [options/*.json](#optionsjson--per-platform-profiles).

---

### aspectConditions.py

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

### aspectHandlers.py

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

#### handleAnnotatedAspect (`pointcut == '@aspect'`)

Activates code that is parked inside the target file as a comment:

```js
/* @aspect'''
    remoteLog.trace('here');
''' */
```

The engine finds each comment, looks for the `@aspect''' … '''` annotation inside it,
and rewrites the file so the comment markers are removed and the inner text becomes
live code. This lets you keep large advice next to the code it touches.

#### addRemoteLog (helper)

A project-specific convenience used as an `onEachFile` post-processor: if an aspect's
advice references `remoteLog`, it ensures the file has
`import * as remoteLog from '~/remote-log';` at the top (inserted after the existing
import block via `textUtil.insertImportStatement`). It is idempotent.

---

### aspectRunners.py

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

### textUtil.py

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

### fileutil.py & printers.py

- `fileutil.readFile` / `writeFile` — plain text IO.
- `fileutil.copyFolderIfEmpty(source, target, minNumberOfFilesInDest)` — copy a folder
  (e.g. the injected `remote-log` library) into the target project only if it isn't
  already there. Used by the driver to seed advisor code before weaving.
- `printers.printError` / `printInfo` — coloured console messages. Note the driver
  treats **any** stdout/stderr from the Python process as a failure signal (see
  [Running the Injector](#running-the-injector)), so the engine stays quiet on success.

## Aspect Dictionary Reference

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

### Targeting keys

| Key             | Type                             | Default                    | Meaning                                                                                                                               |
| --------------- | -------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `file`          | string                           | — (required, group level)  | Target file, relative to the project folder configured in `config.py`.                                                                |
| `pointcut`      | string \| list \| `'@aspect'`    | — (required, aspect level) | Text/pattern selecting the join point(s). A list is tried in order until one matches. `'@aspect'` switches to inline-annotation mode. |
| `match-type`    | `exact` \| `regex` \| `function` | `exact`                    | How `pointcut` is matched. `regex` uses `re.search`; `function` enables argument copying.                                             |
| `trim-pointcut` | bool                             | `True`                     | Strip surrounding whitespace from `pointcut` (so you can use indented triple-quoted strings).                                         |

### Advice keys

| Key           | Type                                         | Default  | Meaning                                                                                                                                      |
| ------------- | -------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `advice`      | string \| `{before, after}`                  | —        | Code to weave. A dict wraps the match (`before` in front, `after` behind); either side may be omitted. Not required when `position: remove`. |
| `position`    | `before` \| `after` \| `replace` \| `remove` | `before` | Where the advice goes relative to the match.                                                                                                 |
| `trim-advice` | bool                                         | `True`   | Strip surrounding whitespace from advice text.                                                                                               |

### Condition keys

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

### Examples

#### Replace a call to wrap it

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

#### Insert after a marker, with parameters from build options

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

#### Restrict to non-production environments

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

#### Optional replace that tolerates a missing pointcut

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

#### Wrap a function call, copying its real arguments (`match-type: function`)

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

### Inline `@aspect` annotations

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
[handleAnnotatedAspect](#handleannotatedaspect-pointcut--aspect).)

---

### Composing multiple aspect lists in one file

A definition module can build its `aspects` list from several blocks — handy for
grouping related rules:

```python
aspects = [ ... core rules ... ]

errorBoundary = [ { "file": ..., "aspects": [ ... ] } ]

aspects.extend(errorBoundary)
```

## Building a Definition Project

A **definition project** is a normal Python package that owns _what_ to inject and
_where_. It contains two kinds of artefact:

1. **Aspect dictionaries** — Python modules exposing `aspects` lists (the rules).
2. **Advisors / payload code** — the actual code that gets injected or copied.

The engine never imports your definition project directly; the **driver** does, after
you put the project on `PYTHONPATH`. So a definition project's only hard requirement is:
_be importable, and expose `aspects` lists in modules the driver names._

### Layout Example

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
│       └── …                   # adobe/, observable/, iterative/, video/, youview/, …
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

### Writing an aspect module

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

See [Aspect Dictionary Reference](#aspect-dictionary-reference) for every key you can use.

### Advisors / payload code

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

### When an aspect is the wrong tool: patches

For changes too large or too structural for text pointcuts (e.g. multi-file vendor
edits), `.../patches/<branch>/<ticket>/…` stores raw `.patch` files applied by
the driver/build outside the injector. Treat patches as the escape hatch; prefer
aspects for anything you want to keep readable and condition-aware.

### Design guidance

- **Keep advice minimal and idempotent.** Inject a call, not a body. The default
  `skip-if-advice-found` then protects you from double injection.
- **Gate by `env`/`branch`** so debug-only concerns never reach production builds.
- **Mark fragile pointcuts `optional`** so a refactor in the main project degrades
  gracefully instead of failing the build — but only where a silent skip is acceptable.
- **Prefer `match-type: function`** when wrapping calls whose arguments you don't want
  to hard-code.

## Wiring an App / Driver Layer

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

### The entry point (`index.py` / `__main__.py`)

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

### Config (`config.py`)

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

### Actions (`actions.py`)

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

#### The `onEachFile` hook

`runAspectIn` calls `onEachFile(aspect, file, content)` after each successful weave. The
real driver uses it for two cross-cutting follow-ups:

- **Import injection** — when `self.extraAspects == 'remoteLog'`, it calls
  `aspectHandlers.addRemoteLog(...)` so any file that now references `remoteLog` gets the
  import added.
- **Linting** — when `self.afterProcess == 'lint'`, it registers each touched `.js` file
  with an `ESLint` helper, run at the end via `executeESLint()` to auto-fix formatting
  of the injected code.

The demo's hook is a no-op (`return '', content`) — post-processing is optional.

#### Copy-then-weave helpers

- `copyRemoteLogFolder()` → `fileutil.copyFolderIfEmpty(...)` seeds the advisor library,
  then runs `configure_remote_aspect()`.
- `copyStaticRemoteLogFile()` → `shutil.copyfile(...)` seeds `remoteLogs.js`, then weaves
  references to it.

---

### Adding a new app

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

### Adding a new job to an existing app

1. Write/extend an aspect module in the definition project (e.g.
   `html5App/aspects/mytrace.py`).
2. Add a method on the actions class that imports it and calls `runAspectIn(...)`.
3. Add an `elif self.job == 'my-trace':` branch in `execute(...)`.
4. (Optional) add a shell wrapper — see [Running the Injector](#running-the-injector).

## Running the Injector

### PYTHONPATH — the glue

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

### Direct CLI invocation

#### Bundled demo (self-contained)

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

#### Real driver (with options/extra)

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

### options/\*.json — per-platform profiles

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

### The shell drivers

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

#### Environment variables the shell layer expects

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

### Where this fits in a build

Typical order during a deploy:

1. Check out the main project into `$react_html5_projectfolder`.
2. Export `PYTHONPATH` (engine + definition project).
3. Run the relevant `aspect_html5_*` shell functions (or `index.py` directly) to weave
   in the required concerns for the target `--env`/`--branch`/`--options`.
4. Build the now-modified target project as normal.

The main project's own repository is never modified — only the checked-out working copy
that gets built.

## End-to-End Walkthrough

This walks through the self-contained demo shipped with the engine. It needs no
definition project — the aspects live in `html5/aspects/sampleJob.py`. The commands and
output below were run and verified.

### The pieces involved

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

### Run it

```bash
cd .../code-injector
export PYTHONPATH=.../code-injector
python3 . --app html5 --job sample_job --branch main --version 1.0.0 --env dev
```

The process exits `0` and **prints nothing** on success (recall: success = silence).

### Target before

```js
// This code will be modified as configured in html5/aspects/sampleJob.py

let a = 5
let b = 10
```

### Target after

```js
// This code will be modified as configured in html5/aspects/sampleJob.py

let a = 5
console.log('Assigned a to 5')
console.log('About to assign b to 10')
let b = 10
```

Note how each injected line lands on its **own** line — `ContentRange.getSeparators`
inserted the needed `\n` without adding blank-line noise.

### What happened, step by step

1. `__main__.py` parsed the args and called `context.createApp('html5', 'main', '1.0.0', 'dev')`.
2. `Html5AppAction('sample_job').execute()` dispatched to `__sample_job_aspect()`.
3. That imported `html5.aspects.sampleJob` and called `runAspectIn(aspects, './sampleCode', onEachFile, context)`.
4. The engine resolved `./sampleCode/sample.js`, read it, and for each inner aspect:
   - `checkAspectCondition` passed (no conditions, advice not yet present);
   - `handleAspect` found the pointcut and inserted the advice (`after` `let a = 5;`,
     `before` `let b = 10;`).
5. The file was written back.

### Idempotency check

Run the **same command again**. Because `skip-if-advice-found` defaults to `True`, the
engine sees its own `console.log(...)` advice already present and skips both aspects —
the file is unchanged, no duplicate logs. (To prove it to yourself, run twice and diff.)

### Restoring the sample

The demo edits the file in place. To get the original back:

```bash
cd .../code-injector
git checkout -- sampleCode/sample.js
```

(In a real build the target is a throwaway checkout, so in-place editing is fine and
the source repo is never touched — see [Where this fits in a build](#where-this-fits-in-a-build).)

### From demo to real use

| Demo                                                | Real                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------- |
| Aspects in `html5/aspects/sampleJob.py` (same repo) | Aspects in `.../html5App/aspects/*.py` (separate project)           |
| `folder = "./sampleCode"`                           | `folder = os.environ['react_html5_projectfolder']` (build checkout) |
| One job `sample_job`                                | Many jobs: `inject_logging`, `performance`, `auto_signin`, …        |
| No-op `onEachFile`                                  | Lint + `remoteLog` import injection                                 |
| `python .` by hand                                  | `aspect_html5_*` shell functions inside the deploy pipeline         |

You now have the full picture: the [engine](#engine-architecture) is generic, the
[definition project](#building-a-definition-project) supplies the rules and payload, and the
[driver](#wiring-an-app--driver-layer) orchestrates them per [build context and
platform](#running-the-injector). You may also go further by reading through the [opening build story](#start-here-a-build-story)

## Tiny Boot Lab

This lab supports the first story in the tutorial. It modifies only the local
`lab/app` copy.

```bash
./scripts/reset.sh
./scripts/run.sh
sed -n '1,120p' app/src/app.js
```
