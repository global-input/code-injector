import sys
import getopt
import codeInjector.context
from html5.actions import Html5AppAction


configArguments = ['branch=', 'version=', 'env=', "job=", "app="]


def getConfigArguments():
    return configArguments[:]


class ArgumentProcessor:
    def processArguments(self, argv):
        try:
            opts, args = getopt.getopt(argv, "", configArguments)
        except getopt.GetoptError:
            print('invalid arguments expecting:{expected}'.format(
                expected=" ".join(configArguments)))
            sys.exit(2)

        for opt, arg in opts:
            if opt == '--branch':
                self.branch = arg
            elif opt == '--version':
                self.version = arg
            elif opt == '--env':
                self.env = arg
            elif opt == "--job":
                self.job = arg
            elif opt == '--app':
                self.app = arg
            else:
                print('invalid arguments expecting:{expected}'.format(
                    expected=" ".join(configArguments)))

        codeInjector.context.createApp(
            self.app, self.branch, self.version, self.env)

    def execute(self):
        if self.app == 'html5':
            html5AppAction = Html5AppAction(self.job)
            html5AppAction.execute()


def main(argv):
    argumentProcessor = ArgumentProcessor()
    argumentProcessor.processArguments(argv)
    argumentProcessor.execute()


if __name__ == "__main__":
    main(sys.argv[1:])
