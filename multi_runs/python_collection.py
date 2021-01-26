"""-----------------------------------------------------------------------------

    python_collection.py - LR, January 2021

    Functionality for a collective Python script with multiple runs.

-----------------------------------------------------------------------------"""
from . import RunCollection, RunScript
from .py_scripts.plain_template import get_plain_template
from .py_scripts.fancy_template import get_fancy_template


class PythonRunCollection(RunCollection):
    """ Single Python script that holds all the jobs.
    """
    def __init__(self, *args , **kwargs):
        super().__init__(*args, **kwargs)
        self.out_file = 'run.py'

    def __str__(self):
        return "Python run with {:d} jobs.".format(len(self.jobs))

    def create_scripts(self, shebang="#!/usr/bin/python", fancy=None):
        """ Interface for the creation of SLURM/batch scripts.
        """
        self.script = self._create_python_script(fancy=fancy)
        print(self.script)
        self.script.persist(shebang=shebang)

    def _create_python_script(self, fancy=None):
        """ Sort of ugly but effective.
        """
        if not len(self.jobs):
            raise ValueError("No jobs - no script!")

        if fancy:
            py_prologue, py_epilogue = get_fancy_template(fancy, split=True)
        else:
            py_prologue, py_epilogue = get_plain_template(split=True)

        # list all jobs.
        py_job_lines = ['    jobs = [']
        for k, job in enumerate(self.jobs):
            py_job_lines.append('        Job("{:s}", "{:s}", "{:d}/{:d}"), '.format(job.path, self.code_execution, k+1, len(self.jobs)))
        py_job_lines.append('    ]')

        # actually execute with controlled number of processes.
        str_nproc = "n_proc = {:d}".format(self.exec_param['n_threads'])
        py_epilogue[0] = py_epilogue[0].replace('#nproc', str_nproc)

        # Produce a script and add it to the list of scripts we produced.
        return RunScript(
            preamble=py_prologue,
            main_text=py_job_lines,
            epilogue=py_epilogue,
            filename=self.root+self.out_file,
            info_param={
                'n_jobs' : len(self.jobs),
                'n_threads' : self.exec_param["n_threads"]
            }
        )
