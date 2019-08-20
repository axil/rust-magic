from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)
from subprocess import run, PIPE, STDOUT, Popen
from textwrap import dedent
from time import perf_counter as clock
import os
import tempfile

__version__ = '0.3.0'

from contextlib import contextmanager

@contextmanager
def cwd(path):
    oldpwd=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)

def calc_hash(s):
    return ('%04x' % hash(s))[-4:]

@magics_class
class MyMagics(Magics):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_dir = tempfile.TemporaryDirectory()
        print(self.temp_dir.name)

    @line_cell_magic
    def rust(self, line, cell=None):
        "Magic that works both as %lcmagic and as %%lcmagic"
        print_wrapper =  dedent('''\
                fn main(){
                    println!("{:?}", (||{
                        %s
                    })());
                }\
        ''')
        run_wrapper =  '''\
                fn main(){
                    %s
                }\
        ''' 
        cmd = ['cargo', 'script']
        if cell is None:
            if line.rstrip().endswith(';'):
                body = run_wrapper % line
            else:
                body = print_wrapper % line
        else:
            opts = line.strip()
            if opts:
                cmd.extend(opts.split('#', 1)[0].split())
            if 'fn main(' in cell:
                body = cell
            else:
                if cell.rstrip().endswith(';'):
                    body = run_wrapper % cell
                else:
                    body = print_wrapper % cell
        with cwd(self.temp_dir.name):
            filename = 'cell-%s.rs' % calc_hash(body)
            open(filename, 'w').write(body)
            cmd.append(filename)
            with Popen(cmd, stdout=PIPE, stderr=STDOUT) as proc:
                while True:
                    line = proc.stdout.readline()
                    if line:
                        print(line.decode().rstrip())
                    else:
                        break
    
    @line_cell_magic
    def trust(self, line, cell=None):
        t1 = clock()
        self.rust(line, cell)
        t2 = clock()
        print('Took %.0f ms' % ((t2-t1)*1000))


def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)
