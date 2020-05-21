"""-----------------------------------------------------------------------------

    multi_run.py - LR, May 2020

    

-----------------------------------------------------------------------------"""
import sys, re, os, shutil, stat, time, datetime, hashlib, copy, json
import numpy as np
from copy import deepcopy, copy

class SLURMRunCollection(object):
    """	Container for creating the direcory tree and all that is necessary for
        that.
    """
    def __init__(self, jobs, fixed_dict, exec_param):
        # Set defaults & update with given values.
        self.exec_param = {
            'executable' : None,
            'sep' : '!',
            'order' : [],
            'preamble_commands' : [],
            'job_preamble' : [],
            'threads' : 1,
            'minutes' : 0,
            'memory' : 2496,
            'inp' : 'setup.inp',
            'log' : 'logfile.log',
            'exec_command' : './{exec} -i {inp} -o {log}',
            'dir' : 'run',
            'type' : 'slurm',
            'config' : 'json',
        }
        self.exec_param.update(exec_param)

        # Build the command to execute the code.
        self.code_execution = self.exec_param['exec_command'].replace('{inp}', exec_param['inp'])
        self.code_execution = self.code_execution.replace('{log}', exec_param['log'])
        if self.exec_param['executable'] is not None:
            self.code_execution = self.code_execution.replace('{exec}', self.exec_param['executable'])
        self.code_execution += ' &'
        print(self.code_execution)

        # Set the root.
        self.root = os.getcwd() + "/" + self.exec_param['dir'] + '/'
        self.out_file = 'run.sh'

        # Initialize the list of the scripts that are produced.
        self.scripts = []
        self.jobs = []
        for job in jobs:
            job.update(fixed_dict)
            self.jobs.append(JohnJob(job, root=self.root))

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
            else:
                raise NotImplementedError('Type of configuration file not supported!')

            # Copy the executable and make it executable.
            if self.exec_param['executable'] is not None:
                shutil.copyfile(self.exec_param['executable'], job.path + self.exec_param['executable'])
                st = os.stat(job.path + self.exec_param['executable'])
                os.chmod(job.path + self.exec_param['executable'], st.st_mode | stat.S_IEXEC)


    def create_scripts(self):
        """ Interface for the creation of SLURM/batch scripts.
        """
        if self.exec_param['type'] == 'slurm':
            self._create_SLURM_scripts()

        elif self.exec_param['type'] == 'batch':
            self._create_batch_script()

        else:
            raise NotImplementedError('Format of specified run not supported.')

        # Now write all scripts to disk.
        for script in self.scripts:
            script.persist()


    @classmethod
    def distribute_tasks_to_nodes(cls, n_tasks, max_threads, n_threads):
        """ Takes the number of jobs, the maximal number of threads per node and
            the number of threads per job and returns a distribution of nodes.

            Example:
                >>> n_tasks = 20, max_threads = 6, threads = 2
                [3, 3, 3, 3, 3, 3, 2]

        """
        # Get how many jobs we can fit on one node.
        max_jobs = max_threads // n_threads

        # Calculate number of nodes to request.
        n_nodes = n_tasks//max_jobs + (1 if n_tasks % max_jobs else 0)

        return np.array([n_tasks//n_nodes + int(k < n_tasks%n_nodes) for k in range(n_nodes)])


    def _create_SLURM_scripts(self, modules=[]):
        """ Creates a possibly splitted SLURM script.
        """

        # Calculate the node distribution.
        node_jobs = self.distribute_tasks_to_nodes(
            n_tasks=len(self.jobs),
            max_threads=self.exec_param['max_cores'],
            n_threads=self.exec_param['threads']
        )

        # Some general settings for the scripts, the same across possibly splitted
        # files.
        slurm_preamble = [
            "#SBATCH --partition=" + self.exec_param['partition'],
            "#SBATCH --mem-per-cpu={:d}\n".format(self.exec_param['memory']),
            "#SBATCH --mail-type=FAIL",
            "#SBATCH --nodes=1",
        ]
        if 'constraint' in self.exec_param:
           slurm_preamble.append("#SBATCH --constraint="+self.exec_param['constraint'])

        # Final lines of the script, same across possibly splitted files.
        slurm_epilogue = ['\n\nwait']

        for n, n_jobs in enumerate(node_jobs):
            if len(node_jobs) > 1:
                filename = (self.out_file[::-1].replace('.', '_{:d}.'.format(n+1)[::-1], 1))[::-1]
            else:
                filename = self.out_file

            n_low, n_up = sum(node_jobs[:n]), sum(node_jobs[:n+1])

            # Set the required hours.
            hours = np.max([job.exec_hours for job in self.jobs[n_low:n_up]])
            if hours == 0:
                hours = self.exec_param['hours']

            # Node specific sets.
            slurm_job_lines = [
                "#SBATCH --time={:02d}:{:02d}:{:02d}".format(hours, self.exec_param['minutes'], 0),
                "export OMP_NUM_THREADS={:d}".format(self.exec_param['threads']),
                "#SBATCH --cpus-per-task={:d}".format(self.exec_param['threads']),
                "#SBATCH --job-name={:s}_{:d}".format(self.exec_param['executable'], n+1),
                "#SBATCH --ntasks={:d}\n".format(n_jobs)
            ]

            for command in self.exec_param['preamble_commands']:
               slurm_job_lines.append(command)
            slurm_job_lines.append("\n\n")

            # One set of commands for every job.
            for job in self.jobs[n_low:n_up]:
                # Switch to the directory.
                slurm_job_lines.append("cd " + job.path)

                # Possibly set up the stage.
                for command in self.exec_param['job_preamble']:
                   slurm_job_lines.append(command)

                # Execute the code.
                slurm_job_lines.append(self.code_execution)

                # Switch back.
                slurm_job_lines.append("cd " + self.root)
                slurm_job_lines.append("sleep 0.5\n")


            # Produce a script and add it to the list of scripts we produced.
            slurm_script = JohnScript(
                preamble=slurm_preamble,
                main_text=slurm_job_lines,
                epilogue=slurm_epilogue,
                filename=self.root+filename,
                info_param={
                    'n_jobs':n_jobs,
                    'n_threads':self.exec_param['threads'],
                    'maxcores':self.exec_param['max_cores']
                    }
            )
            self.scripts.append(slurm_script)
            print(slurm_script)


    def _create_batch_script(self, modules=[]):
        """ Creates a batch script.
        """
        # TODO: implement multi-threaded runs at some point.
        batch_preamble = [
            'maxcores={:d}'.format(self.exec_param['max_cores']),
            'export OMP_NUM_THREADS={:d}\n'.format(1)
        ]

        # list all jobs.
        batch_job_lines = ['declare -a jobs=(']
        for k in range(len(self.jobs)):
            batch_job_lines.append(
                '"cd {:s}; echo [{:s}] job {:d}/{:d}; {:s}"'.format(
                    self.jobs[k].path,
                    time.strftime("%d.%m.%y, %H:%M"),
                    k+1, len(self.jobs),
                    self.code_execution[:-1]
                )
            )
        batch_job_lines.append(')')

        # actually execute with controlled number of processes.
        batch_epilogue = [
            '. ~/Code/utils/john/batch_parallel_defs.sh',
            '. ~/Code/utils/john/batch_parallel.sh'
        ]

        batch_script = JohnScript(
            preamble=batch_preamble,
            main_text=batch_job_lines,
            epilogue=batch_epilogue,
            filename=self.root+self.out_file,
            info_param={
                'n_jobs' : len(self.jobs),
                'n_threads' : self.exec_param['threads'],
                'maxcores' : self.exec_param['max_cores']
                }
        )
        self.scripts.append(batch_script)
        print('\tproduced one script with {:d} tasks ({:d} tasks in parallel)'.format(len(self.jobs), self.exec_param['max_cores']))



class JohnScript(object):
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
            f.write('# This script was produced by JOHN at {:s} \n'.format(datetime.datetime.now().strftime("%d.%m.%Y, %H:%M:%S")))
            f.write('#\n')
            f.write('################################################################################\n\n\n')


            # Write the actual content.
            list(map(lambda t: wrt(t, f), self.preamble))
            list(map(lambda t: wrt(t, f), self.main_text))
            list(map(lambda t: wrt(t, f), self.epilogue))



class JohnJob(object):
    """ Information on a single, separate run.
    """
    def __init__(self, param, root=''):
        """ Initializes with a set of parameters.
        """
        self.param = param
        keystr = str(param) + " " + str(time.time())
        self.id = hashlib.md5(keystr.encode('utf-8')).hexdigest()
        self.path = root + '/job_'+self.id+'/'
        self.exec_hours = 0

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
