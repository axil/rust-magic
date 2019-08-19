from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)
from subprocess import run, PIPE
from textwrap import dedent

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
        opt = ''
        if cell is None:
            if line.rstrip().endswith(';'):
                body = run_wrapper % line
            else:
                body = print_wrapper % line
        else:
            opt = line.strip()
            if opt:
                opt += ' '
            if 'fn main(' in cell:
                body = cell
            else:
                if cell.rstrip().endswith(';'):
                    body = run_wrapper % cell
                else:
                    body = print_wrapper % cell
        open('cell.rs', 'w').write(body)
        res = run(f'cargo script {opt}cell.rs'.split(), stdout=PIPE, stderr=PIPE)
        if res.returncode == 0:
            print(res.stdout.decode().rstrip())
        else:
            print(res.stderr.decode().rstrip())

def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)
