import getopt
import sys

import codeInjector.context
from hello.actions import HelloAction


ARGUMENTS = ["branch=", "version=", "env=", "job=", "app="]


class Arguments:
    def __init__(self):
        self.branch = ""
        self.version = ""
        self.env = ""
        self.job = ""
        self.app = ""

    def parse(self, argv):
        try:
            opts, _ = getopt.getopt(argv, "", ARGUMENTS)
        except getopt.GetoptError:
            print("invalid arguments")
            sys.exit(2)

        for opt, arg in opts:
            if opt == "--branch":
                self.branch = arg
            elif opt == "--version":
                self.version = arg
            elif opt == "--env":
                self.env = arg
            elif opt == "--job":
                self.job = arg
            elif opt == "--app":
                self.app = arg

        codeInjector.context.createApp(
            self.app, self.branch, self.version, self.env)


def main(argv):
    args = Arguments()
    args.parse(argv)

    if args.app == "hello":
        HelloAction(args.job).execute()
    else:
        print("unknown app: {app}".format(app=args.app))
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])

