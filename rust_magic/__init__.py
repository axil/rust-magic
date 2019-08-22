from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)
import sys
import glob
import re
from subprocess import run, PIPE, STDOUT, Popen
from textwrap import dedent
from time import perf_counter as clock
import os
import tempfile

__version__ = '0.3.1'

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

def construct_rs(mline, cell):
    print_wrapper =  dedent('''\
            #[allow(unused)]
            fn main(){
                println!("{:?}", (||{
                    %s
                })());
            }\
    ''')
    run_wrapper =  dedent('''\
            #[allow(unused)]
            fn main(){
                %s
            }\
    ''')
    cmd = ['cargo', 'script']
    mline = mline.strip()
    if cell is None:
        if mline.rstrip().endswith(';'):
            body = run_wrapper % mline
        else:
            body = print_wrapper % mline
    else:
        if mline:
            cmd.extend(mline.split('#', 1)[0].split())
        if 'fn main(' in cell:
            body = cell
        else:
            cell = cell.rstrip()
            if cell.endswith(';'):
                wrapper = run_wrapper
            else:
                wrapper = print_wrapper
            lines = cell.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('//') or \
                line.startswith('extern crate') or \
                line.startswith('use ') or \
                line.strip() == '':
                    pass
                else:
                    break
            body = '\n'.join(lines[:i] + [wrapper % '\n'.join(lines[i:])])
    return cmd, body

@magics_class
class MyMagics(Magics):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_dir = '.rust_magic'
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)
#        self.temp_dir = tempfile.TemporaryDirectory()
#        print('Working dir:', self.temp_dir.name)

    @line_cell_magic
    def rust(self, mline, cell=None):
        "Magic that works both as %lcmagic and as %%lcmagic"
        cmd, body = construct_rs(mline, cell)
        with cwd(self.work_dir):
            #filename = 'cell-%s.rs' % calc_hash(body)
            filename = 'cell.rs'
            open(filename, 'wb').write(body.encode('utf8'))
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

if __name__ == '__main__':
    ok = True
    for test_name in glob.glob(os.path.join('..', 'tests', '*.txt')):
        fin = open(test_name)
        mline = fin.readline()
        if '%rust ' in mline:
            mline = mline.split('%rust ', 1)[1]
        cell = fin.read() or None
        cmd, body = construct_rs(mline, cell)
        expect = open(re.sub('\.txt$', '.rs', test_name)).read()
#        if 'four_cell' in test_name:
#            import ipdb; ipdb.set_trace()
        if body != expect:
            print(test_name + ' failed:\n' + body + '\n!= expected\n' + expect)
            ok = False
        else:
            sys.stdout.write('.')
            sys.stdout.flush()
    if ok:
        print('\nok')

