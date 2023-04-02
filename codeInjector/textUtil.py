import re    
class BlockRange:
   def __init__(self):
       self.start = -1
       self.end = -1
   def length(self):
       return self.end - self.start

class TagRange:
     def __init__(self):
         self.start = BlockRange()
         self.end = BlockRange()

class ContentRange:
    def __init__(self, content):
        self.start = 0
        self.end = len(content)
        self.content = content
        self.separator = '\n'
    def ifFinished(self):
        return self.start >= self.end
    def getPrecedingPart(self, range):
        return self.content[:range.start]
    def getFoundPart(self, range):
        return self.content[range.start:range.end]
    def getRemainingPart(self, range):
        return self.content[range.end:]
    def getFoundAndRemainingPart(self, range):
        return self.content[range.start:]
    def getPrecedingAndFoundPart(self, range):
        return self.content[:range.end]    
    def isNewLine(self,start,end, step):    
        for i in range(start, end, step):
           if self.content[i] == self.separator:
               return True
           elif self.content[i] > ' ':
              return False
        return True
    def getSeparators(self, start):
        isPrecedingNewLine=self.isNewLine(start-1, -1,  -1)        
        isFollowingNewLine=self.isNewLine(start, self.end, 1)        
        if isPrecedingNewLine and isFollowingNewLine:
            return '',''
        elif isPrecedingNewLine:
            return '', self.separator
        elif isFollowingNewLine:
            return self.separator, ''
        else:
           return '',''

    def removeFound(self, range):
        self.content = self.getPrecedingPart(range) + self.getRemainingPart(range)
        self.end = len(self.content)
        self.start=range.start
    def replaceFound(self, range, text):
        self.content = self.getPrecedingPart(range) + text + self.getRemainingPart(range)
        self.end = len(self.content)
        self.start=range.start+len(text)   
    def insertToFront(self, range, text):
        fSeparator,bSeparator=self.getSeparators(range.start)        
        self.content = self.getPrecedingPart(range) + fSeparator+text + bSeparator+self.getFoundAndRemainingPart(range)        
        self.end = len(self.content)
        self.start=range.start+len(fSeparator)+len(text)+len(bSeparator)+range.length()
        
    def insertAfter(self, range, text):
        fSeparator,bSeparator=self.getSeparators(range.end)
        self.content = self.getPrecedingAndFoundPart(range)  + fSeparator+text +bSeparator+ self.getRemainingPart(range)
        self.end = len(self.content)
        self.start=range.end+len(fSeparator)+len(text)+len(bSeparator)
    def insertToFrontAndAfter(self, range, before,after):
        fSeparator1,bSeparator1=self.getSeparators(range.start)
        fSeparator2,bSeparator2=self.getSeparators(range.end)
        self.content = self.getPrecedingPart(range) + fSeparator1+before + bSeparator1 + self.getFoundPart(range) + fSeparator2 + after + bSeparator2 + self.getRemainingPart(range)
        self.end = len(self.content)
        self.start=range.start+len(fSeparator1)+len(before)+len(bSeparator1)+range.length()+len(fSeparator2)+len(after)+len(bSeparator2)
        

def tagNotFound(tag):
    return tag.start.start < 0 or tag.end.start < 0

def findChacaters(content, start, end):
    if start >= end:
        return -1
    for i in range(start, end):
        if content[i] > ' ':
            return i
    return -1


def findEndOfLine(content, start, end):
    if start>=end:
        return -1
    for i in range(start, end):
        if content[i] == '\n':
            return i
    return end    
    
def findCode(content, start,end):    
    while start<end:
        start=findChacaters(content,start, end)
        if start<0:
           return -1        
        commentIndex=content.find('//', start, start+5)
        if commentIndex == start:
            lineEndIndex=findEndOfLine(content,commentIndex+2, end)
            if lineEndIndex < 0 :
                return -1
            start=lineEndIndex+1
            continue
        commentIndex=content.find('/*', start, start+5) 
        if commentIndex == start:
            commentEndIndex=content.find('*/', commentIndex+2, end)
            if commentEndIndex < 0:
                return -1
            start=commentEndIndex+2
            continue
        return start
    return -1

def findHeadStatementInsertPosition(content, start, end, statementBegin, statementEnd,maxStatementLength):
    insertAt=-1
    def getInsertAt(default):
        if insertAt >=0:
            return insertAt
        else:
            return default

    while start < end:
        codeindex=findCode(content,start,end)
        if codeindex < 0:
            return getInsertAt(start)           
        start=codeindex
        codeindex = content.find(statementBegin,start, start+maxStatementLength)
        if codeindex == start:
            codeindex = content.find(statementEnd,start+len(statementBegin), end)
            if codeindex < 0 :                             
                return getInsertAt(start)                
            start=codeindex+len(statementEnd)
            insertAt = start            
        else:
            return getInsertAt(start)            
    return getInsertAt(start)
    

def insertImportStatement(content, importBlock):
    index = findHeadStatementInsertPosition(content, 0, len(content), "import ", ";",10)
    if index < 0:
        return importBlock+"\n" + content
    elif index >= len(content):
        return content+ "\n" + importBlock
    else:
        return content[0:index] + "\n"+  importBlock +"\n"+content[index:]   

def findTag(content, start, end, startTag, EndTag):      
   tagRange = TagRange()         
   tagRange.start.start = content.find(startTag, start, end)
   if tagRange.start.start < -1:
       return tagRange
   tagRange.start.end = tagRange.start.start+len(startTag)

   tagRange.end.start =  content.find(EndTag, tagRange.start.end, end)
   if tagRange.end.start >=0:
       tagRange.end.end = tagRange.end.start + len(EndTag)
   return tagRange    

def findComment(content, start, end):      
   line = findTag(content, start, end, '//', '\n')
   if line.start.start > 0 and line.end.start  < 0:
       line.end.start = line.end.end = end
   elif line.end.end:
       line.end.end=line.end.end-1

   block =  findTag(content, start, end, '/*', '*/')   
   if tagNotFound(line) and tagNotFound(block) :
       return line
   elif tagNotFound(line):
       return block
   elif tagNotFound(block):
       return line
   elif line.start.start < block.start.start:
       return line
   else:
       return block


def findAdviceAnnotation(content, start, end):
    return findTag(content, start, end, "@aspect'''", "'''")


def fineTextExact(contentRange, textToFind):
    range=BlockRange()
    range.start = contentRange.content.find(textToFind, contentRange.start, contentRange.end)
    if range.start < 0:
        return range    
    range.end = range.start + len(textToFind)   
    return range

def findTextWithRegex(contentRange, regExpression):
    range=BlockRange()
    if(contentRange.start == 0 and contentRange.end == len(contentRange.content)):
        res=re.search(regExpression, contentRange.content)
    else:
        res=re.search(regExpression, contentRange.content[contentRange.start:contentRange.end])
    if res:
        range.start = res.start()
        range.end = res.end()        
    return range

def findText(contentRange, textToFind, matchType):
    if matchType == 'exact' or matchType == 'function':
        return fineTextExact(contentRange, textToFind)
    elif matchType == 'regex':
        return findTextWithRegex(contentRange, textToFind)
    else:
        return BlockRange()


def parse_parentheses(content, function_name):
    start_index = content.find(function_name + '(')
    if start_index == -1:
        return None

    start_index += len(function_name)

    end_index = content.find(')', start_index)
    if end_index == -1:
        return None

    between = content[start_index+1:end_index]

    return between

def replace_parameters(function_call, function_name, new_parameters):
    parameters_start = function_call.find(function_name + '(') + len(function_name)
    parameters_end = function_call.find(')', parameters_start)
    return function_call[:parameters_start+1] + new_parameters + function_call[parameters_end:]

def copyInputParameters(content, search, replace):
    search_function_name = search.split('(')[0].strip()
    replace_function_name = replace.split('(')[0].strip()

    content_parameters = parse_parentheses(content, search_function_name)

    if content_parameters is None:
        raise None

    new_search = replace_parameters(search, search_function_name, content_parameters)
    new_replace = replace_parameters(replace, replace_function_name, content_parameters)

    return (new_search, new_replace)



if __name__ == "__main__":
   testText="1 2 3 dilshat 232"
   range=findText(testText, "dilshat", 0, len(testText),'exact')
   print(range.start, range.end)

