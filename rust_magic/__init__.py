from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)
from subprocess import run, PIPE, STDOUT, Popen
from textwrap import dedent

__version__ = '0.2.5'

@magics_class
class MyMagics(Magics):
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
        opts = ''
        if cell is None:
            if line.rstrip().endswith(';'):
                body = run_wrapper % line
            else:
                body = print_wrapper % line
        else:
            opts = line.strip()
            if opts:
                opts = opts.split('#', 1)[0] + ' '
            if 'fn main(' in cell:
                body = cell
            else:
                if cell.rstrip().endswith(';'):
                    body = run_wrapper % cell
                else:
                    body = print_wrapper % cell
        open('cell.rs', 'w').write(body)
        with Popen(f'cargo script {opts}cell.rs'.split(), stdout=PIPE, stderr=STDOUT) as proc:
            while True:
                line = proc.stdout.readline()
                if line:
                    print(line.decode().rstrip())
                else:
                    break

def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)
