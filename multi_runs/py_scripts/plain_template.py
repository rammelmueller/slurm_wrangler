def get_plain_template(split=True):
    py_prologue_lines = [
        "from multiprocessing import Pool",
        "from datetime import datetime",
        "import os",
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
        "        p.map(job_starter, jobs)"
    ]

    # Return list of lines.
    if split:
        return py_prologue_lines, py_epilogue_lines

    # Return as text.
    sep = " \n"
    return sep.join(py_prologue), sep.join(py_epilogue)
