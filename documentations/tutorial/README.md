# Code Injector - Starts with a Build Story

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

## First Win: Prove the App Reached Boot

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
cd /Users/user/workspace/utils/code-injector/documentations/tutorial/lab
./scripts/reset.sh
./scripts/run.sh
sed -n '1,120p' app/src/app.js
```

Run `./scripts/run.sh` again. The log line will not be duplicated. The injector notices
that the advice is already present and skips it.

## The First Real Trick: Make Typing on a TV Remote Disappear

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

## The Moment It Becomes a Product: Give the Debug Library a Config

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

## Turn Existing Logs Into Remote Logs

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

## Follow a Request From Start to Failure

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

## Redirect Hard-Coded Vendor Hosts Without Touching Vendor Code

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

## Make Branch Differences Boring

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

## Measure Performance Without Rebuilding the App by Hand

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

## When the Build Itself Needs a Small Rescue

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

## When the Payload Is Too Big, Keep It Beside the Aspect

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

## The Pattern to Remember

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
