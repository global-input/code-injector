import sys

import codeInjector.aspectRunners
import codeInjector.context
import hello.config


class HelloAction:
    def __init__(self, job):
        self.job = job
        self.context = codeInjector.context.getAppContext(hello.config.name)

    def on_each_file(self, aspect, file, content):
        return "", content

    def boot_reached(self):
        import helloApp.aspects.bootReached
        codeInjector.aspectRunners.runAspectIn(
            helloApp.aspects.bootReached.aspects,
            hello.config.folder,
            self.on_each_file,
            self.context)

    def execute(self):
        if self.job == "boot_reached":
            self.boot_reached()
        else:
            print("unknown job: {job}".format(job=self.job))
            sys.exit(2)

