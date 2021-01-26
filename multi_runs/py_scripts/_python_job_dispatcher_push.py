from multiprocessing import Pool
from datetime import datetime
import os, subprocess
from pushover import Client


def _send(msg, device):
    client = Client("uwxqcfqmy67k1iyfvo3t74ej9no47r", api_token="ahyydd79r5ymfc2nj91a4bcnyg9qmg")
    client.send_message(
        msg['text'],
        title=msg['title'],
        device=device
    )

def _timestamp():
    return datetime.now().strftime("%b %d %Y %H:%M:%S")

def push_finished_run(run, device='oneplus_t3_luki'):
    msg = {
        'title' : 'Run completed!',
        'text' : f"The script with {run['n_tasks']} tasks @{run['host']} finished at {_timestamp()}"
    }
    _send(msg, device=device)



class Job(object):
    def __init__(self, dir, command, label):
        self.label = label
        self.dir = dir
        self.command = command

    def __str__(self):
        return self.label + " " + self.dir

    def run(self):
        os.system("cd " + self.dir + "; " + self.command)


def job_starter(job):
    print("[" + str(datetime.now()) + "] " + str(job))
    job.run()

if __name__ == '__main__':

    #jobs

    #nproc
    with Pool(n_proc) as p:
        p.map(job_starter, jobs)


    run = {
        'host': subprocess.check_output(['hostname']).strip().decode('UTF-8'),
        'n_tasks' : len(jobs)
    }
    push_finished_run(run)
