import codeInjector.fileutil
import codeInjector.aspectHandlers
import codeInjector.printers
import codeInjector.aspectConditions


def isPointIsNotFound(message):
    return message.find('text:') >= 0  and message.find('not found') >= 0

def processPointFunctionCall(aspect, content):
    pointcut=aspect.get('pointcut')
    if pointcut == None:
        return False
    elif pointcut == '@aspect':
        return False
    matchType=aspect.get('match-type','exact')    
    if(matchType != 'function'):
        return False
    if(type(pointcut) != str):
        return False
    pointcut=pointcut.strip()
    advice=aspect.get('advice')
    if(type(advice) != str):
        return False
    advice=advice.strip()
    newSearchAndReplace=codeInjector.textUtil.copyInputParameters(content, pointcut, advice)
    if newSearchAndReplace == None:
        return False
    aspect['pointcut']=newSearchAndReplace[0]
    aspect['advice']=newSearchAndReplace[1]
    return True
    
 
    
    




def runAspectIn(aspects, folder, onEachFile, context):
    for i, aspect in enumerate(aspects):
        file = aspect["file"]
        filepath = folder+'/'+file
        if not codeInjector.aspectConditions.checkAspectCondition(aspect, context, file):
            continue

        content = codeInjector.fileutil.readFile(filepath)

        for k, ap in enumerate(aspect["aspects"]):
            if not codeInjector.aspectConditions.checkAspectCondition(ap, context, file, content):
                continue

            message, content = codeInjector.aspectHandlers.handleAspect(
                ap, content, context)
            if(isPointIsNotFound(message)):
                if(processPointFunctionCall(ap, content)):
                    message, content = codeInjector.aspectHandlers.handleAspect(
                        ap, content, context)
            if message != "":
                codeInjector.printers.printError(
                    "{message} in {file}".format(message=message, file=filepath))
            else:
                message, content = onEachFile(ap, file, content)
                if message != "":
                    codeInjector.printers.printError(
                        "{message} in {file}".format(message=message, file=filepath))

        codeInjector.fileutil.writeFile(filepath, content)
