#!/usr/bin/env python3

def readFile(filename):    
    f = open(filename,'r')
    filedata = f.read()
    f.close()    
    return filedata

def writeFile(filename, content):
    f = open(filename,'w')
    f.write(content)
    f.close()


def copyFolderIfEmpty(source, target, minNumberOfFilesInDest):
    import shutil
    import os.path
    if os.path.exists(target): 
        if os.path.isfile(target):
            shutil.delete(target)
            shutil.copytree(source, target)
            return True
        elif  os.path.isdir(target):
            if len(os.listdir(target)) < minNumberOfFilesInDest:
                shutil.rmtree(target)  
                shutil.copytree(source, target)
                return True
            else:
                return False
        else:
            shutil.copytree(source, target)
            return True
    else:           
        shutil.copytree(source, target)
        return True


    