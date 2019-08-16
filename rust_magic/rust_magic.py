from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)
import subprocess

@magics_class
class MyMagics(Magics):
    @line_cell_magic
    def rust(self, line, cell=None):
        "Magic that works both as %lcmagic and as %%lcmagic"
        wrapper =  '''\
                fn main(){
                    println!("{}", (||{%s})());
                }\
        '''           
        if cell is None:
            body = wrapper % line
        elif 'fn main(' in cell:
            body = cell
        else:
            body = wrapper % cell
        open('cell.rs', 'w').write(body)
        res = subprocess.run('cargo script cell.rs'.split(), capture_output=True)
        if res.returncode == 0:
            print(res.stdout.decode().rstrip())
        else:
            print(res.stderr.decode().rstrip())

def load_ipython_extension(ipython):
    ipython.register_magics(MyMagics)
