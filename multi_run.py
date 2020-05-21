"""-----------------------------------------------------------------------------

    multi_run.py - LR, May 2020



-----------------------------------------------------------------------------"""
import sys, re, os, shutil, stat, time, datetime, hashlib, copy, json, yaml
import numpy as np
from copy import deepcopy, copy


class SLURMRunCollection(object):
    """	Container for creating the direcory tree and all that is necessary for
        that.
    """
    def __init__(self, jobs, fixed_dict, exec_param, slurm):
        # Set defaults & update with given values.
        self.exec_param = {
            'copy_files' : [],
            'sep' : '!',
            'order' : [],
            'preamble_commands' : [],
            'job_preamble' : [],
            'inp' : 'setup.inp',
            'log' : 'logfile.log',
            'exec_command' : './{exec} -i {inp} -o {log}',
            'dir' : 'run',
            'type' : 'slurm',
            'config' : 'json',
        }
        self.exec_param.update(exec_param)
        self.slurm = slurm

        # To implement at a later stage.
        self.multi_job_script = False

        # Build the command to execute the code.
        self.code_execution = self.exec_param['exec_command'].replace('{inp}', exec_param['inp'])
        self.code_execution = self.code_execution.replace('{log}', exec_param['log'])
        self.code_execution += ' &'

        # Set the root.
        self.root = os.getcwd() + "/" + self.exec_param['dir'] + '/'
        self.out_file = 'run.sh'

        # Initialize the list of the scripts that are produced.
        self.scripts = []
        self.jobs = []
        for job in jobs:
            job.update(fixed_dict)
            self.jobs.append(SingleJob(job, root=self.root))

    def __str__(self):
        return "Run with {:d} jobs.".format(len(self.jobs))

    def create_populated_directories(self):
        """	Physically creates directories and copies everything necessary for
            a successful run.
        """
        for job in self.jobs:
            if not os.path.exists(job.path):
                os.makedirs(job.path)

            # Produce appropriate config file.
            if self.exec_param['config'] == 'plain':
                job.create_plain_config(filename=self.exec_param['inp'], sep=self.exec_param['sep'], order=self.exec_param['order'])
            elif self.exec_param['config'] == 'json':
                job.create_JSON_config(filename=self.exec_param['inp'])
            elif self.exec_param['config'] == 'yaml':
                job.create_YAML_config(filename=self.exec_param['inp'])
            else:
                raise NotImplementedError('Type of configuration file not supported!')

            # Copy the executables and make them executable.
            for cpfile in self.exec_param['copy_files']:
                shutil.copyfile(cpfile, job.path + cpfile)
                st = os.stat(job.path + cpfile)
                os.chmod(job.path + cpfile, st.st_mode | stat.S_IEXEC)


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



class SingleJob(object):
    """ Information on a single, separate run.
    """
    def __init__(self, param, root=''):
        """ Initializes with a set of parameters. A job ID from the parameters
            and the current time is created. The details don't matter actually,
            this is essentially a random but unique identifiier.
        """
        self.param = param
        keystr = str(param) + " " + str(time.time())
        self.id = hashlib.md5(keystr.encode('utf-8')).hexdigest()
        self.path = root + '/job_'+self.id+'/'

    def __str__(self):
        return self.path

    def create_plain_config(self, filename="setup.inp", order=[], sep='!'):
        """	Creates a plain text config file in the directory self.path
        """
        with open(self.path + filename, 'w') as c_file:
            # First order the specified ones.
            for key in order:
                c_file.write("{0} {1} {2}\n".format(key, sep, self.param[key]))
            # Then loop through the rest.
            for key in set(self.param.keys()).difference(set(order)):
                c_file.write("{0} {1} {2}\n".format(key, sep, self.param[key]))


    def create_JSON_config(self, filename="setup.inp"):
        """	Creates a JSON config file in the directory self.path.
        """
        with open(self.path + filename, 'w') as c_file:
            list(map(c_file.write, json.dumps(self.param, sort_keys=True, indent=4, separators=(',', ' : '))))


    def create_YAML_config(self, filename="setup.inp"):
        """	Creates a JSON config file in the directory self.path.
        """
        with open(self.path + filename, 'w') as f:
            yaml.dump(self.param, f, default_flow_style=False)
