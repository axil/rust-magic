# rust-magic [![Build Status](https://travis-ci.org/axil/rust-magic.svg?branch=master)](https://travis-ci.org/axil/rust-magic)

Allows to try rust in Jupyter notebook. Implemented via line/cell magics:

<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/rust-magic.png" width="600">

## Installation

1. Install rust and jupyter-notebook

2. `cargo install cargo-script`

3. `pip install rust-magic`

4. Enjoy :)

## Third-party crates

are supported via normal `cargo script` syntax:

<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/external-crate.png" width="600">

## Compiler options

can be provided in the cell mode:

<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/debug1.png" width="800">

Copy-pastable form of the examples on [github](https://github.com/axil/rust-magic/blob/master/example.ipynb) or in
[nbviewer](https://nbviewer.jupyter.org/github/axil/rust-magic/blob/master/example.ipynb).

## Syntax highlighting

To enable rust syntax highlighting in %%rust cells run the following snippet in a python jupyter cell:
```
from notebook.services.config import ConfigManager
c = ConfigManager()
c.update('notebook', {"CodeCell": {"highlight_modes": {"text/x-rustsrc": {"reg": ["^%%rust"]}}}})
```

It only needs to be run once: it stores the setting in a config file in home directory.

## Long cells

Jupyter "doesn't like" long cells: when a cell gets longer than the screen its output is not readily visible.
Here're a few ways how to handle it with rust_magic:

a) putting dependencies into a separate cell
<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/deps.png" width="600px">

b) collapsing function bodies with codefolding jupyter extension
<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/collapsed.png" width="600px">

c) putting function definitions into separate cells
<img src="https://raw.githubusercontent.com/axil/rust-magic/master/img/rust_fn1.png" width="600px">
