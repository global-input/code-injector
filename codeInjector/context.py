
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


def getAppContext(appName):
    createAppIfEmpty(appName)
    return apps[appName]



      

    
    



