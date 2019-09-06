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
import sys
from textwrap import dedent
try:
    from time import perf_counter as clock
except:     # python2.7 compatibility
    import time
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
    }
'''), ' '*8

run_wrapper =  dedent('''\
    #[allow(unused)]
    fn main(){
    %s
    }
'''), ' '*4

def eq(a, b):
    if a != b:
        print('%s != %s' % (a, b))
        sys.exit(1)

cur_func_name = lambda n=0: sys._getframe(n + 1).f_code.co_name

def normalize_dep(dep):
    return ' = '.join(re.split('\s*=\s*', dep))

def parse_deps_line(s):
    return [(k, v if v else '"*"') for (k, v) in 
        re.findall('\s*([a-zA-Z-]+)\s*(?:=\s*((?:{[^}]*})|(?:"[^"]*")))?', s)]

def test_parse_deps_line():
    eq(parse_deps_line("ndarray, ndarray-rand, rand"), 
        [('ndarray', '"*"'), ('ndarray-rand', '"*"'), ('rand', '"*"')])
    eq(parse_deps_line('''\
            ndarray = {git = "https://github.com/rust-ndarray/ndarray.git"}, \
            array="0.12.1"'''),
        [('ndarray', '{git = "https://github.com/rust-ndarray/ndarray.git"}'),
         ('array', '"0.12.1"')])
    eq(parse_deps_line('ndarray="0.12.1", ndarray-rand="0.9.0", rand="0.7.0"'),
        [('ndarray', '"0.12.1"'), ('ndarray-rand', '"0.9.0"'), ('rand', '"0.7.0"')])
    print(cur_func_name() + ' ok')

def construct_rs(mline, cell, deps={}, funcs={}, feats=[]):
    cmd = ['cargo', 'script']
    mline = mline.strip()
    body = ''
    if deps:
        body = deps_template % '\n'.join('//! %s = %s' % d for d in deps.items())
        if feats:
            for feat in feats:
                body += '#![feature(%s)]\n' % feat
        for dep in deps:
            body += 'extern crate %s;\n' % dep.replace('-', '_')
    elif feats:
        for feat in feats:
            body += '#![feature(%s)]\n' % feat
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

if sys.version_info[:3] < (3,6,0):
    from collections import OrderedDict
    odict = OrderedDict
else:
    odict = dict

@magics_class
class MyMagics(Magics):
    def __init__(self, *args, **kwargs):
        super(MyMagics, self).__init__(*args, **kwargs)
        self.work_dir = '.rust_magic'
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)
        self.deps = odict()
        self.funcs = {}
        self.feats = []
#        self.temp_dir = tempfile.TemporaryDirectory()
#        print('Working dir:', self.temp_dir.name)

    @line_cell_magic
    def rust(self, mline, cell=None):
        '''
        %rust/%%rust runs code in the line/cell.
        %rust -v/--version prints version of rust_magic
        '''
        if cell is None and mline.strip() in ('-v', '--version'):
            print('rust_magic v%s' % __version__)
            return
        cmd, body = construct_rs(mline, cell, self.deps, self.funcs, self.feats)
#        with cwd(self.work_dir):
           #filename = 'cell-%s.rs' % calc_hash(body)
        filename = os.path.join(self.work_dir, 'cell.rs')
        open(filename, 'wb').write(body.encode('utf8'))
        cmd.append(filename)
        os.environ['RUSTC_WRAPPER'] = 'sccache'
        with Popen(cmd, stdout=PIPE, stderr=STDOUT) as proc:
            while True:
                line = proc.stdout.readline()
                if line:
                    print(line.decode().rstrip())
                else:
                    break

    @line_cell_magic
    def trust(self, line, cell=None):
        '''
        Same as %rust/%%rust but also measures total elapsed time
        '''
        t1 = clock()
        self.rust(line, cell)
        t2 = clock()
        print('Took %.0f ms' % ((t2-t1)*1000))

    @line_cell_magic
    def rust_deps(self, line, cell=None):
        '''
        One or more dependencies with version numbers separated by semicolon, eg
        %rust_deps ndarray = "0.12.1"; glob = "0.3.0"
        Use -l/--list to see currently configured deps:
        %rust_deps --list
        Use -c/--clear to clear the list of deps:
        %rust_deps --clear
        '''
        chunks = []
        line = line.strip()
        only = False
        if cell is None:
            while True:
                parts = line.split(None, 1)
                if parts and parts[0].startswith('-'):
                    if len(parts) == 2:
                        opt, tail = parts
                    else:
                        opt, tail = parts[0], ''
                    if opt in ('-c', '--clear'):
                        self.deps.clear()
                        line = ''
                        break
                    elif opt in ['-l', '--list']:
                        line = ''
                        break
                    elif opt in ['-o', '--only']:
                        only = True
                    else:
                        print('Unknown option:', opt)
                        return
                    line = tail
                else:
                    break
            chunks = ["%s = %s" % (a, b) for a, b in parse_deps_line(line)]
        else:
            chunks = cell.splitlines()
        if chunks:
            news = odict(re.split('\s*=\s*', d, 1) for d in chunks if d)
            if only:
                self.deps = news
            else:
                self.deps.update(news)
        s = (', ' if cell is None else '\n').join(['%s = %s' % (k, v) for k, v in self.deps.items()])
        print('Deps:', s if s else '<none>')

    @line_magic
    def rust_feat(self, line):
        line = line.strip()
        if line in ('-c', '--clear'):
            self.feats = []
        elif line not in ('-l', '--list'):
            if line not in self.feats:
                self.feats.append(line)
        print(self.feats)

    @line_cell_magic
    def rust_fn(self, line, cell=None):
        '''
        Function definitions block with optional name.
        -l/--list see currently configured function blocs:
           %rust_fn --list
        -c/--clear to clear the list of function blocks:
           %rust_fn --clear
        -b/--build  runs current cell after others in the list
        -o/--only  runs current cell only
        '''
        parts = line.split('//', 1)[0].strip().split()
        flags, name = [], ''
        for p in parts:
            if p[0] == '-':
                flags.append(p)
            else:
                name = p
        if ('-b' in flags or '--build' in flags) and cell is not None:
            if name in self.funcs:
                del self.funcs[name]
            self.rust('', cell)
        elif ('-o' in flags or '--only' in flags) and cell is not None:
            backup = self.funcs
            self.funcs = {}
            self.rust('', cell)
            self.funcs = backup
        elif '-c' in flags or  '--clear' in flags:
            self.funcs.clear()
        if cell is None:
            if '-l' not in flags and '--list' not in flags and name in self.funcs:
                del self.funcs[name]
        else:
            self.funcs[name] = cell
        print('Funcs:', list(self.funcs.keys()))


def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)

def parse_deps_cell(s):
    return odict(re.split('\s*=\s*', d, 1) for d in s.splitlines() if d)

def test_construct_rs():
    ok = True
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for test_name in glob.glob(os.path.join(project_dir, 'tests', 'deps2.txt')):
        fin = open(test_name)
        mline = fin.readline()
        if '%rust ' in mline:
            mline = mline.split('%rust ', 1)[1]
        cell = fin.read() or None
        deps_fn = re.sub('\.txt', '.deps', test_name)
        if os.path.exists(deps_fn):
            deps = open(deps_fn).read()
        else:
            deps = ''
        cmd, body = construct_rs(mline, cell, parse_deps_cell(deps))
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
        print('\n' + cur_func_name() + ' ok')
    else:
        sys.exit(1)

def test_deps():
    m = MyMagics()
    m.rust_deps('a="1"')
    eq(m.deps, {'a': '"1"'})
    m.rust_deps(' -l ')
    eq(m.deps, {'a': '"1"'})
    m.rust_deps('--list')
    eq(m.deps, {'a': '"1"'})
    m.rust_deps('', 'a="1"\nb="2"')
    eq(m.deps, {'a': '"1"', 'b': '"2"'})
    m.rust_deps('c="3",d={git = "www"}')
    eq(m.deps, {'a': '"1"', 'b': '"2"', 'c': '"3"', 'd': '{git = "www"}'})
    m.rust_deps('--clear')
    eq(m.deps, {})
    print(cur_func_name() + ' ok')

def test_funcs():
    m = MyMagics()
    m.rust_fn('f', 'f()')
    eq(m.funcs, {'f': 'f()'})
    m.rust_fn('-l')
    eq(m.funcs, {'f': 'f()'})
    m.rust_fn('--list')
    eq(m.funcs, {'f': 'f()'})
    m.rust_fn('f // comment', 'g()')
    eq(m.funcs, {'f': 'g()'})
    m.rust_fn('h', 'h()')
    eq(m.funcs, {'f': 'g()', 'h': 'h()'})
    m.rust_fn('--clear')
    eq(m.funcs, {})
    print(cur_func_name() + ' ok')

if __name__ == '__main__':
    test_parse_deps_line()
    test_construct_rs()
    test_deps()
    test_funcs()
