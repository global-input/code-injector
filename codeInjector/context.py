
class ContextInfo:
    branch=""
    version=""
    env=""

apps={}


def createAppIfEmpty(appName):
    if apps.get(appName)==None:
        apps[appName]=ContextInfo()    

def createApp(appName, branch="", version="", env=""):
    createAppIfEmpty(appName)
    apps[appName].branch=branch
    apps[appName].version=version
    apps[appName].env=env   
    return apps[appName]

REPLACE_IDENTIFIER="REPLACE:"    

def setVersionSuffix(appName, versionSuffix):
    app = apps.get(appName)
    if app is not None and app.version is not None:
        if versionSuffix.startswith(REPLACE_IDENTIFIER):
            app.version = versionSuffix[len(REPLACE_IDENTIFIER):]  # Replace the version with the string after '---'
        else:
            app.version += versionSuffix


def getAppContext(appName):
    createAppIfEmpty(appName)
    return apps[appName]



      

    
    



