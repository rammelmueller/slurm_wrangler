"""-----------------------------------------------------------------------------

    slurm_collection.py - LR, May 2020

    Functionality for multiple SLURM runs.

-----------------------------------------------------------------------------"""
import datetime
from . import RunCollection

class SLURMRunCollection(RunCollection):
    """	SLURM specific implementation.
    """
    def __init__(self, slurm, *args , **kwargs):
        super().__init__(*args, **kwargs)
        self.slurm = slurm
        self.out_file = 'run.sh'

    def __str__(self):
        return "SLURM Run with {:d} jobs.".format(len(self.jobs))

    def create_scripts(self):
        """ Interface for the creation of SLURM/batch scripts.
        """
        if self.multi_job_script:
            raise NotImplementedError('only single slurm scripts supported for now, sorry')
        else:
            self.scripts = self._create_single_SLURM_scripts()
        for script in self.scripts:
            script.persist()

    def _create_single_SLURM_scripts(self):
        """ Creates a single SLURM script per job - ASC style.
        """
        # Translate the SLURM parameters.
        slurm_preamble = []
        for k, v in self.slurm.items():
            slurm_preamble.append(f'#SBATCH --{k}={v}')

        # Final lines of the script, same across possibly splitted files.
        slurm_epilogue = ['\n\nwait']

        # Create a script for every job.
        scripts = []
        for n, job in enumerate(self.jobs):
            filename = (self.out_file[::-1].replace('.', '_{:d}.'.format(n+1)[::-1], 1))[::-1]

            # Anything that should be executed before the job runs (module loading..)
            slurm_job_lines = []
            for command in self.exec_param['preamble_commands']:
               slurm_job_lines.append(command)
            slurm_job_lines.append("\n\n")

            # One set of commands for every job
            slurm_job_lines.append(self.code_execution)
            slurm_job_lines.append("sleep 0.5\n")

            # Some job-specifc slurm lines.
            sjl = [
                '#SBATCH --chdir={:s}'.format(job.path),
                '#SBATCH --output={:s}'.format(job.path+self.exec_param['log']),
                '#SBATCH --error={:s}\n\n'.format(job.path+'error.log'),
            ]

            # Produce a script and add it to the list of scripts we produced.
            slurm_script = RunScript(
                preamble=slurm_preamble + sjl,
                main_text=slurm_job_lines,
                epilogue=slurm_epilogue,
                filename=self.root+filename,
                info_param={
                    'n_jobs' : 1,
                    'n_threads' : 1,
                    'maxcores' : 1
                    }
            )
            scripts.append(slurm_script)
            print(slurm_script)

        return scripts




class RunScript(object):
    """   A class that represents a script file.
    """
    def __init__(self, preamble=[], main_text=[], epilogue=[], filename=None, info_param=None):
        """ Set up everything to
        """
        self.preamble = preamble
        self.epilogue = epilogue
        self.main_text = main_text
        self.filename = filename
        self.info_param = info_param


    def __str__(self):
        return "{:s}: script has {:d} tasks ({:d} of {:d} threads used).".format(
            self.filename,
            self.info_param['n_jobs'], self.info_param['n_threads']*self.info_param['n_jobs'],
            self.info_param['maxcores'])


    def persist(self):
        """ Write the script to its file.
        """
        if self.filename is None:
            raise IOError('No filename specified for script.')

        wrt = lambda t, f: f.write(t + '\n')
        with open(self.filename, 'w') as f:

            # Write some information.
            f.write('#!/bin/bash\n')
            f.write('################################################################################\n')
            f.write('#\n')
            f.write('# This script was produced by slurm_wrangler at {:s} \n'.format(datetime.datetime.now().strftime("%d.%m.%Y, %H:%M:%S")))
            f.write('#\n')
            f.write('################################################################################\n\n\n')


            # Write the actual content.
            list(map(lambda t: wrt(t, f), self.preamble))
            list(map(lambda t: wrt(t, f), self.main_text))
            list(map(lambda t: wrt(t, f), self.epilogue))
