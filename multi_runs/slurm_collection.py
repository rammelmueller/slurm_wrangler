"""-----------------------------------------------------------------------------

    slurm_collection.py - LR, May 2020

    Functionality for multiple SLURM runs.

-----------------------------------------------------------------------------"""
from . import RunCollection, RunScript


class SLURMRunCollection(RunCollection):
    """	SLURM specific implementation.
    """
    def __init__(self, slurm, *args , **kwargs):
        super().__init__(*args, **kwargs)
        self.slurm = slurm
        self.out_file = 'run.sh'

        # Add this for parallel support.
        self.code_execution += ' &'

    def __str__(self):
        return "SLURM run with {:d} jobs.".format(len(self.jobs))

    def create_scripts(self):
        """ Interface for the creation of SLURM/batch scripts.
        """
        if self.multi_job_script:
            raise NotImplementedError('only single slurm scripts supported for now, sorry')
        else:
            self.scripts = self._create_single_SLURM_scripts()
        for script in self.scripts:
            script.persist(shebang="#!/bin/bash")


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
