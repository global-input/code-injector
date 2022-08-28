
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

def setVersionSuffix(appName, versionSuffix):
    if(apps[appName]!=None and apps[appName].version!=None):
        apps[appName].version=apps[appName].version+versionSuffix
        


def getAppContext(appName):
    createAppIfEmpty(appName)
    return apps[appName]



      

    
    



