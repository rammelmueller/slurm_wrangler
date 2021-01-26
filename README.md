slurm_wrangler
====================================
Simple command-line utility to produce batches of [SLURM](https://slurm.schedmd.com/documentation.html) runs that need to be executed under the same conditions (environment etc.). Nothing fancy, but gets the job(s) done.

## Purpose
The purpose of the script `slurm_wrangler.py` is to generate a list of jobs, each of which in an automatically generated (and uniquely named) directory along with a script that is able to run all those jobs under the requested conditions (e.g., SLURM environment).

Although the main use-case is SLURM-based clusters, there is also an option to generate a simple Python script (toggled via a command line flag) that runs locally on the number of specified threads. All SLURM-type commands will be disregarded in this case, though.


## Usage
All you need to do to generate the specified run(s) is to issue
```
   python slurm_wrangler.py -i <config.yml> [-local]
```
which will read all relevant information from the input file (to be described below). The `-local` flag toggles whether a SLURM style run is generated or a *single Python script* that executes the list of jobs with a Pool of `N` threads. While the former option is quite useful for computing clusters, tha latter is convenient for local runs on a machine under your control.

### Input
The YAML input file holds all relevant information on the physical parameters, hyper-parameters and environment parameters for your simulations. A sample configuration (`rbatch.inp`) is provided in the repository. Here's a brief description of the relevant types of parameters:

 - `fixed`: A list of parameter values that are constant for all runs, passed unaltered to the simulation script.
 - `variable`: This is a list of parameters which will be expanded such that all combinations are generated. The name of the parameter is the name of a node in the YAML file, it should have two subfields:
    - `values`: The list of parameter values to iterate.
    - `order`: Th, planned for the future thoughe order in which the paramters are expanded (index in the tuple, so to say). Ensure, that this is a contiguous list starting at `1`. This parameter is actually not that important, mostly here for historic reasons and most probably will be removed at some point.

 - `exec_param`: A collection of settings that toggle the behavior of the script / simulation, mostly I/O and environment related. A brief overview:
   - `dir` (default='run/'): The directory in which everyting is generated.
   - `config` (default='yaml'): Either 'yaml' or 'json ' for the respective format of the produced input file. These files will hold the parameters and are then the input file to your simulation code - so your code needs to support the specified format. Although heavyily discuraged: If plain-text is required, this can be accommodated by adding an appropriate class method to the class `SingleJob` (same goes for all other forms of input).
   - `inp` (default='setup.inp'): Name of the input file (which holds all the simulation parameters) that is generated.
   - `log` (default='lofile.log'): Name of a logfile that holds all output (if used by your code).
   - `exec_command` (**required**): This is the command that will be executed to actually run your code. Here's a two examples:
      - `./dummy -i {inp} -o {log}`: Assumes an executable file 'dummy' is present in the directory (which can be copied with `copy_files`, see below). The fields `{inp}` and `{log}` will be replaced with the values specified above.
      - `python <path/to/script> -i {inp} -o {log}`: No executable needed here, the code is simply called from the location where the code is stored. Replacement as above.
      - `julia --project=<path/to/code> <path/to/script> {inp}`: Julia version of the above.
   Generally, you can chain together as many things that you would want here. Multiple different input files are not supported at this point, but might be a viable option in the future (although YAML style input does not really require this).
   - `copy_files` (default=[]): A list of files that is copied to each run directory. This is intended to be the executable(s) for the required runs plus any additionally required files.
   - `preamble_commands`: A list of commands that are called in each script before jobs are submitted. Each line in this node reflects a shell-command that is issued. The inended use is to set environment variables or load Python virtual environments, set debug flags etc.
   - `job_preamble`: Similar to the above, but these commands will be executed before every job (so to say a "local" job environment). The working directory is *in the directory of a single job*. This is useful for instance when you have a lot of output and want to store it in a subdirectory there. Then, simply add `mkdir <output_dir>` to this list and it will be generated in every job directory before the run is issued.
 - `slurm_param`: Those are the SLRUM commands which are invoked in the script that is sent to the queue. They are exactly as desribed in the SLURM documentation and are simply passed through.

### Output (SLURM)
Invoking the script as above, with the sample config files will produce the directory `run/` with a sub-directory for every simulation to run later. In this case, there are four. Also, there are four bash scripts in this directory. Each of them will look similar to this:

```
   #!/bin/bash
   ################################################################################
   #
   # This script was produced by slurm_wrangler at 26.01.2021, 08:36:11
   #
   ################################################################################
   #SBATCH --ntasks=1
   #SBATCH --ntasks-per-node=1
   #SBATCH --nodes=1
   #SBATCH --time=01:00:00
   #SBATCH --chdir=./run/job_aa786e1b41a75fe3eea3198db61fe8db/
   #SBATCH --output=./run/job_aa786e1b41a75fe3eea3198db61fe8db/logfile.log
   #SBATCH --error=./run/job_aa786e1b41a75fe3eea3198db61fe8db/error.log

   source /path/to/venv/bin/activate

   ./dummy -i setup.inp -o logfile.log &
   sleep 0.5

   wait
```

This can now be sent to SLURM by simply invoking `sbatch <scriptname>` and already you're in the queue.


### Output (local)
If you used the `-local` flag, all job directories will be the same but the job script is slightly different. Instead of (potentially separate) bash scripts there will be a single Python script which will run your jobs in place of the SLURM scheduler. To run it, simply type
```
   python <name_of_script> --nthreads=<number of threads>
```
where the flag defines how many jobs are run in parallel. The default is single core.   




## Notes
 - Multiple jobs per SLURM scripts are not supported as of now (planned).
 -
