"""-----------------------------------------------------------------------------

    slurm_wrangler.py - LR, May 2020

    Takes in ranges of parameters and produces batch files that execute the
    specified executable with the desired input parameters. A directory is
    created that contains a subfolder per set of parameters, marked by an
    explicit ID.

    Input is toggled via a yaml file, that has several entries:

        - fixed:        parameters that are the same for all runs
        - variable:     values are specified in lists and are unpacked at the top
                        level
        - exec_param:   everything that is needed for proper execution / setup
                        of the enviroment
        - slurm:        SLURM specific commands

    A more complete overview is in the README.

    Usage:

            python slurm_wrangler.py -i <input_file.yml>

-----------------------------------------------------------------------------"""
import argparse, os, sys, yaml
from expander import expand_dict
from multi_runs import SLURMRunCollection, PythonRunCollection


parser = argparse.ArgumentParser(description='SLURM wrangler.',
    formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-i', metavar='input', type=str, nargs='?', default=None,
    help=("Input batch file.\n\n")
)
parser.add_argument('-local', action='store_true', help='Toggls python style.')
args = parser.parse_args()


# Read the parameters from the yaml file.
with open(args.i, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Make the list of jobs.
jobs = expand_dict(config.get('variable', None))
for p in config['param_sets']:
    jobs.append(p)

# Choose the type an create.
if args.local:
    run = PythonRunCollection(jobs, config['fixed'], config['exec_param'])
else:
    run = SLURMRunCollection(config['slurm'], jobs, config['fixed'], config['exec_param'])

# Persist to disk.
run.create_populated_directories()
run.create_scripts()
