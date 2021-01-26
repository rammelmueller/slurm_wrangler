"""-----------------------------------------------------------------------------

    multi_run.py - LR, May 2020



-----------------------------------------------------------------------------"""
import sys, re, os, shutil, stat, time, datetime, hashlib, copy, json, yaml
import numpy as np
from copy import deepcopy, copy


class RunCollection(object):
    """	Container for creating the direcory tree and all that is necessary for
        that.
    """
    def __init__(self, jobs, fixed_dict, exec_param):
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

        # To implement at a later stage.
        self.multi_job_script = False

        # Build the command to execute the code.
        self.code_execution = self.exec_param['exec_command'].replace('{inp}', exec_param['inp'])
        self.code_execution = self.code_execution.replace('{log}', exec_param['log'])
        self.code_execution += ' &'

        # Set the root.
        self.root = os.getcwd() + "/" + self.exec_param['dir'] + '/'

        # Initialize the list of the scripts that are produced.
        self.scripts = []
        self.jobs = []
        for job in jobs:
            job.update(fixed_dict)
            self.jobs.append(SingleJob(job, root=self.root))


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
