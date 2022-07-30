# code-injector

This is a python script for injecting code into another project using the aspect-oriented programming concept.

## Usage

An example of usage exists in the `html5/` folder which injects code into `sampleCode/sample.js` based on the aspects found in `html5/aspects/sampleJob.py`

To see it in action:

```
git clone https://github.com/global-input/code-injector
cd code-injector
python . --app html5 --job sample_job --branch [BRANCH] --version [VERSION] --env [ENV]
```