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

    Usage:

            python slurm_wrangler.py -i <input_file.yml>

-----------------------------------------------------------------------------"""
import argparse, os, sys, yaml
from expander import expand_dict
from multi_run import RunCollection

parser = argparse.ArgumentParser(description='RICHARD - the lionheart.',
    formatter_class=argparse.RawTextHelpFormatter)

# General i/O parameters.
parser.add_argument('-i', metavar='input', type=str, nargs='?', default=None,
    help=("Input batch file.\n\n")
)

# ------------------------------------------------------------------------------
args = parser.parse_args()


# Read the parameters from the yaml file.
with open(args.i, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
jobs = expand_dict(config['variable'])

run = SLURMRunCollection(jobs, config['fixed'], config['exec_param'], config['slurm'])
run.create_populated_directories()
run.create_scripts()
