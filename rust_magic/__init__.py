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

__version__ = '0.3.2'

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

print_wrapper = dedent('''\
        #[allow(unused)]
        fn main(){
            println!("{:?}", (||{
        %s
            })());
        }\
'''), ' '*8

run_wrapper =  dedent('''\
        #[allow(unused)]
        fn main(){
        %s
        }\
'''), ' '*4

def construct_rs(mline, cell):
    cmd = ['cargo', 'script']
    mline = mline.strip()
    if cell is None:
        if len(mline) > 0 and mline[-1] in ';}':
            wrapper = run_wrapper
        else:
            wrapper = print_wrapper
        body = wrapper[0] % (wrapper[1] + mline)
    else:
        if mline:
            cmd.extend(mline.split('#', 1)[0].split())
        if 'fn main(' in cell:
            body = cell
        else:
            cell = cell.rstrip()
            lines = cell.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('//') or \
                line.startswith('extern crate') or \
                line.startswith('use ') or \
                line.strip() == '':
                    pass
                else:
                    break
            wrapper = print_wrapper
            for line in reversed(lines[i:]):
                line = line.split('//', 1)[0].rstrip()
                if not line:
                    continue
                if line[-1] in ';}':
                    wrapper = run_wrapper
                break
            body = '\n'.join(lines[:i] + [wrapper[0] % '\n'.join(
                wrapper[1] + line for line in lines[i:])])
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
        cmd, body = construct_rs(mline, cell)
#        with cwd(self.work_dir):
            #filename = 'cell-%s.rs' % calc_hash(body)
        filename = os.path.join(self.work_dir, 'cell.rs')
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
            print(test_name + ' failed:\n' + repr(body) + '\n!= expected\n' + repr(expect))
            ok = False
        else:
            sys.stdout.write('.')
            sys.stdout.flush()
    if ok:
        print('\nok')

