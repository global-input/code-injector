import sys
import re




import codeInjector.aspectConditions      
import codeInjector.textUtil

remoteLogImportText='''import * as remoteLog from '~/remote-log';'''


def addRemoteLog(aspect, content):    
    if content.find(remoteLogImportText) >=0:
        return '', content
    advice=aspect.get('advice','na')        
    if type(advice) == str:
        if advice.find('remoteLog')>=0:
            return '',codeInjector.textUtil.insertImportStatement(content,remoteLogImportText)
        else:
            return "", content
    before=advice.get('before','')
    after=advice.get('after','')

    if type(before) == str and before.find('remoteLog')>=0:
            return '',codeInjector.textUtil.insertImportStatement(content,remoteLogImportText)        
    if type(after) == str and after.find('remoteLog')>=0:
            return '',codeInjector.textUtil.insertImportStatement(content,remoteLogImportText)
    else:
        return "", content

            


def handleAnnotatedAspect(aspect, content,context):
    start=0
    end=len(content)    
    while start<end:
        comment = codeInjector.textUtil.findComment(content, start, end)        
        if codeInjector.textUtil.tagNotFound(comment):
            return ('', content)        
        start=comment.end.end   
        adviceAnnotation = codeInjector.textUtil.findAdviceAnnotation(content, comment.start.end, comment.end.start)        
        if codeInjector.textUtil.tagNotFound(adviceAnnotation):
            start=comment.end.end            
        else:                                    
            advice= content[adviceAnnotation.start.end:adviceAnnotation.end.start]            
            content=content[:comment.start.start] + advice + content[comment.end.end:]
            start=comment.start.start+len(advice)
            end=len(content)        
    return ('', content)        
        


def handleAspect(aspect, content, context):    
    pointcut=aspect.get('pointcut')        
    if pointcut == None:        
        return ('pointcut is missing in the aspect', content)        
    elif pointcut == '@aspect':
        return handleAnnotatedAspect(aspect, content,context)    
    
    if aspect.get('trim-pointcut', True):
        pointcut=pointcut.strip()                
        
    matchType=aspect.get('match-type','exact')    
    contentRange=codeInjector.textUtil.ContentRange(content)
    processCounter=0    
    while contentRange.ifFinished() == False:
        range=codeInjector.textUtil.findText(contentRange, pointcut,matchType)
        
        if range.start == -1:
            if processCounter == 0:
                return ('text:{pointcut}: not found '.format(pointcut=pointcut), content)
            else:
                break
        processCounter=processCounter+1        
        position=aspect.get('position','before')        
        advice=aspect.get('advice')
        if advice == None: 
            if position == 'remove':
                contentRange.removeFound(range)
            else:
                return ('advice is missing in the aspect', content)
        elif type(advice) == str:
            if aspect.get('trim-advice', True):
                advice=advice.strip()
            if position == 'before':
                contentRange.insertToFront(range, advice)                
            elif position == 'after':
                contentRange.insertAfter(range,advice)
            elif position == 'replace':
                contentRange.replaceFound(range,advice)
            elif position == 'remove':
                contentRange.removeFound(range)
            else:
                return ('position is missing in the aspect', content)
        else:
            before=advice.get('before')
            after=advice.get('after')            
            if before == None and after == None:
                return ('advice is missing in the aspect', content)
            elif before == None:
                if(aspect.get('trim-advice', True)):
                    after=after.strip()
                contentRange.insertToFront(range,after)                    
            elif after == None:
                if(aspect.get('trim-advice', True)):
                    before=before.strip()
                contentRange.insertToFront(range,before)
            else:
                if(aspect.get('trim-advice', True)):
                    before=before.strip()
                    after=after.strip()
                contentRange.insertToFrontAndAfter(range,before,after)
    return ('', contentRange.content)
     
