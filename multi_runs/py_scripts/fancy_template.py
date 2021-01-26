def get_fancy_template(api, split=True):
    py_prologue_lines = [
        "from multiprocessing import Pool",
        "from datetime import datetime",
        "import os, subprocess",
        "from pushover import Client",
        "",
        "",
        "def _send(msg, device):",
        "    client = Client('"+api[0]+"', api_token='"+api[1]+"')",
        "    client.send_message(",
        "        msg['text'],",
        "        title=msg['title'],",
        "        device=device",
        "    )",
        "",
        "def _timestamp():",
        "    return datetime.now().strftime('%b %d %Y %H:%M:%S')",

        "def push_finished_run(run, device='oneplus_t3_luki'):",
        "    msg = {",
        "        'title' : 'Run completed!',",
        "        'text' : f\"The script with {run['n_tasks']} tasks @{run['host']} finished at {_timestamp()}\"",
        "    }",
        "    _send(msg, device=device)",
        "",
        "",
        "class Job(object):",
        "    def __init__(self, dir, command, label):",
        "        self.label = label",
        "        self.dir = dir",
        "        self.command = command",
        "",
        "    def __str__(self):",
        "        return self.label + ' ' + self.dir",
        "",
        "    def run(self):",
        "        os.system('cd ' + self.dir + '; ' + self.command)",
        "",
        "",
        "def job_starter(job):",
        "    print('[' + str(datetime.now()) + '] ' + str(job))",
        "    job.run()",
        "",
        "if __name__ == '__main__':"
    ]

    py_epilogue_lines = [
        "    #nproc", # must be the first in this list!
        "    with Pool(n_proc) as p:",
        "        p.map(job_starter, jobs)",
        "",
        "",
        "    run = {",
        "        'host': subprocess.check_output(['hostname']).strip().decode('UTF-8'),",
        "        'n_tasks' : len(jobs)",
        "    }",
        "    push_finished_run(run)",
    ]

    # Return list of lines.
    if split:
        return py_prologue_lines, py_epilogue_lines

    # Return as text.
    sep = " \n"
    return sep.join(py_prologue), sep.join(py_epilogue)
