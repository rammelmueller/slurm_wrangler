"""-----------------------------------------------------------------------------

    multi_run.py - LR, May 2020



-----------------------------------------------------------------------------"""
import sys, re, os, shutil, datetime, stat, time, hashlib, copy, json, yaml
import numpy as np
from copy import deepcopy, copy
from configparser import ConfigParser


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
            'n_threads' : 1,
        }
        self.exec_param.update(exec_param)

        # To implement at a later stage.
        self.multi_job_script = False

        # Build the command to execute the code.
        self.code_execution = self.exec_param['exec_command'].replace('{inp}', exec_param['inp'])
        self.code_execution = self.code_execution.replace('{log}', exec_param['log'])

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
            elif self.exec_param['config'] == 'ini':
                job.create_INI_config(filename=self.exec_param['inp'])
            else:
                raise NotImplementedError('Type of configuration file not supported!')

            # Copy the executables and make them executable.
            for cpfile in self.exec_param['copy_files']:
                shutil.copyfile(cpfile, job.path + cpfile)
                st = os.stat(job.path + cpfile)
                os.chmod(job.path + cpfile, st.st_mode | stat.S_IEXEC)



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
        msg =  "{:s}: script has {:d} tasks.".format(
            self.filename,
            self.info_param['n_jobs']
        )
        if "n_threads" in self.info_param:
            msg += " ({:d} threads used)".format(
                self.info_param['n_threads']
            )
        return msg


    def persist(self, shebang=""):
        """ Write the script to its file.
        """
        if self.filename is None:
            raise IOError('No filename specified for script.')

        wrt = lambda t, f: f.write(t + '\n')
        with open(self.filename, 'w') as f:

            # Write some information.
            f.write(shebang+'\n')
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
        """	Creates a YAML config file in the directory self.path.
        """
        with open(self.path + filename, 'w') as f:
            yaml.dump(self.param, f, default_flow_style=False)


    def create_INI_config(self, filename="setup.inp"):
        """ Creates a INI style config file in the directory self.path.
            Those are the ones read/written by the `configparser` module.

            Notes:
                -   A valid inupt file needs to have sections - this is not
                    checked beforehand. If this is violated, the conversion will
                    throw an error.
                -   Currently only works for one level of sections, so no subections.
        """
        # First we need to translate into sections.
        parser = ConfigParser()
        iparam = copy(self.param)

        delkeys = []
        for key in iparam:
            if "." in key:
                delkeys.append(key)
                parts = key.split(".")
                iparam[parts[0]][parts[1]] = self.param[key] # For multilevel this would have to be done recursively, probably.

        # Delete the original keys separated with dots.
        for key in delkeys:
            del iparam[key]

        # Convert everything to string, which is apparently needed to write the thing.
        for section in iparam:
            for key in iparam[section]:
                iparam[section][key] = str(iparam[section][key])

        # Convert and dump.
        parser.read_dict(iparam)
        with open(self.path + filename, 'w') as f:
            parser.write(f)
