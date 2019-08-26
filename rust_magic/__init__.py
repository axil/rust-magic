#!/usr/bin/env python3

# Copyright (c) 2019, Lev Maximov
# All rights reserved.
# Distributed under the terms of the MIT license:
# http://www.opensource.org/licenses/MIT

from __future__ import print_function
from contextlib import contextmanager
import glob
import os
import re
from textwrap import dedent
try:
    from time import perf_counter as clock
except:     # python2.7 compatibility
    import sys, time
    perf_counter = time.clock if sys.platform == "win32" else time.time
from subprocess import PIPE, STDOUT, Popen
import sys

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)

__version__ = '0.3.2'


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

deps_template = dedent('''\
    //! ```cargo
    //! [dependencies]
    %s
    //! ```
''')

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

def normalize_dep(dep):
    return ' = '.join(re.split('\s*=\s*', dep))

def construct_rs(mline, cell, deps=[], funcs={}):
    cmd = ['cargo', 'script']
    mline = mline.strip()
    body = ''
    if deps:
        body = deps_template % '\n'.join('//! %s' % dep for dep in deps)
        for dep in deps:
            body += 'extern crate %s;\n' % dep.split(' = ')[0]
    if funcs:
        body += '\n'.join(funcs.values())
    if cell is None:
        if len(mline) > 0 and mline[-1] in ';}':
            wrapper = run_wrapper
        else:
            wrapper = print_wrapper
        body += wrapper[0] % (wrapper[1] + mline)
    else:
        if mline:
            cmd.extend(mline.split('//', 1)[0].split())
        if 'fn main(' in cell:
            body += cell
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
            body += '\n'.join(lines[:i] + [wrapper[0] % '\n'.join(
                wrapper[1] + line for line in lines[i:])])
    return cmd, body

@magics_class
class MyMagics(Magics):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_dir = '.rust_magic'
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)
        self.deps = []
        self.funcs = {}
#        self.temp_dir = tempfile.TemporaryDirectory()
#        print('Working dir:', self.temp_dir.name)

    @line_cell_magic
    def rust(self, mline, cell=None):
        cmd, body = construct_rs(mline, cell, self.deps, self.funcs)
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

    @line_cell_magic
    def rust_deps(self, line, cell=None):
        if cell is None:
            self.deps = [d for d in re.split('\s*;\s*', line) if d]
        else:
            self.deps = cell.splitlines()
        self.deps = [normalize_dep(dep) for dep in self.deps]
        print('Dependencies:', self.deps)

    @line_cell_magic
    def rust_fn(self, line, cell=None):
        name = line.split('//', 1)[0]
        if cell is None:
            del self.funcs[name]
        else:
            self.funcs[name] = cell
        print('Functions:', list(self.funcs.keys()))


def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)

if __name__ == '__main__':
    ok = True
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for test_name in glob.glob(os.path.join(project_dir, 'tests', '*.txt')):
        fin = open(test_name)
        mline = fin.readline()
        if '%rust ' in mline:
            mline = mline.split('%rust ', 1)[1]
        cell = fin.read() or None
        deps_fn = re.sub('\.txt', '.deps')
        if os.path.exists(deps_fn):
            deps = open(deps_fn).readlines()
        else:
            deps = []
        cmd, body = construct_rs(mline, cell, deps)
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
