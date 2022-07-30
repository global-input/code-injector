import sys
import html5.config
import codeInjector.context
import codeInjector.fileutil
import codeInjector.aspectRunners
import codeInjector.aspectHandlers


class Html5AppAction:
    def __init__(self, job: str):
        self.job = job
        self.context = codeInjector.context.getAppContext(html5.config.name)

    def __on_each_file(self, aspect, file, content):
        return '', content

    def __sample_job_aspect(self):
        import html5.aspects.sampleJob
        codeInjector.aspectRunners.runAspectIn(
            html5.aspects.sampleJob.aspects, html5.config.folder, self.__on_each_file, self.context)

    def execute(self):
        if self.job == 'sample_job':
            self.__sample_job_aspect()
        else:
            print(
                'index.py --job=<job> got: {job}'.format(job=self.job))
            sys.exit(2)
