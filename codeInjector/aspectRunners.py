import codeInjector.fileutil
import codeInjector.aspectHandlers
import codeInjector.printers
import codeInjector.aspectConditions


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

            if message != "":
                codeInjector.printers.printError(
                    "{message} in {file}".format(message=message, file=filepath))
            else:
                message, content = onEachFile(ap, file, content)
                if message != "":
                    codeInjector.printers.printError(
                        "{message} in {file}".format(message=message, file=filepath))

        codeInjector.fileutil.writeFile(filepath, content)
