#!/usr/bin/env python3

class bcolors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def printError(message):
    print(bcolors.RED+" "+message)
    print(bcolors.RESET+".......")

def printInfo(message):
    print(bcolors.BLUE+" "+message)
    print(bcolors.RESET+"")

