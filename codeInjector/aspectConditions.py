import sys
import re
import os


      


def contextMatch(valueInAspect,valueInContext, illegalTypeValue):    
    if type(valueInAspect) == str:
        return valueInAspect == valueInContext
    elif type(valueInAspect) == list:
        for i, m in enumerate(valueInAspect):
            if m == valueInContext:
                return True
        return False
    return illegalTypeValue
            

    
def checkAspectCondition(aspect, context, file, content=None):
    disabled=aspect.get("disabled", False)
    if disabled:
        return False
                
    env=aspect.get('env')    
    if env != None:
        if contextMatch(env, context.env, False) == False:
            return False

    branch=aspect.get('branch')
    if branch != None:
        if contextMatch(branch, context.branch, False) == False:
            return False
    
    skipForBranch=aspect.get('branch-to-skip')
    if skipForBranch != None:
        if contextMatch(skipForBranch, context.branch, True) == True:
            return False
    
    skipIfFileNotFound=aspect.get('skip-if-file-not-found', False)
    if skipIfFileNotFound:    
        if not os.path.exists(file):
           return False

    if content == None:
        return True
    skipIfNotFound=aspect.get('skip-if-not-found')
    if not skipIfNotFound == None:
        if type(skipIfNotFound) == str:            
            skipIfNotFound=skipIfNotFound.strip()
            if content.find(skipIfNotFound)<0:
                return False
        elif type(skipIfNotFound) == list:
            for i, m in enumerate(skipIfNotFound):
                m=m.strip()
                if content.find(m)<0:
                    return False

    skipIfFound=aspect.get('skip-if-found')
    if not skipIfFound == None:
        if type(skipIfFound) == str:
            if skipIfFound =='na':
                pass
            if content.find(skipIfFound)>=0:
                return False
        elif type(skipIfFound) == list:
            for i, m in enumerate(skipIfFound):
                if content.find(m)>=0:
                    return False
    else:
        advice=aspect.get('advice')
        if advice == None:
            pass
        elif type(advice) == str:
            if aspect.get('trim-advice', True):
                advice=advice.strip()                
            if aspect.get('skip-if-advice-found', True):
                if content.find(advice)>=0:
                    return False            
        else:
            before=advice.get('before')
            if before == None:
                pass
            elif type(before) == str:
                if aspect.get('trim-advice', True):
                    before=before.strip()
                if aspect.get('skip-if-advice-found', True):
                    if content.find(before)>=0:
                        return False                
            after=advice.get('after')
            if after == None:
                pass
            elif type(after) == str:
                if aspect.get('trim-advice', True):
                    after=after.strip()
                if aspect.get('skip-if-advice-found', True):
                    if content.find(after)>=0:
                        return False                
    return True
          





    
    




    
    
    

    
    

        
    
