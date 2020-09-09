# Nanophotometer SPH

> Initiates a socket.io connection to an Implen Nanophotometer, parses sample data, and updates the Eton database

---

## Usage

1. Connect to the database and nanophotometer.
2. Scan barcode, then measure the sample.

---

## Development

### Setup

#### Windows

1. Install [Python](https://www.python.org/). During Python setup, make sure that you add Python to your PATH.
2. Install a [git client](https://git-scm.com/).
3. Open up Git Bash in the folder you'd like to install the program.
4. Go to "Bash" section below.

#### Bash

Clone the respository and go into the new folder:

```shell
$ git clone https://github.com/olichen/nanophotometer_sph.git
$ cd /nanophotometer_sph
```

Use Python's package manager to set up a virtual environment with all the required packages. Pipenv is for package management.

```shell
$ pip install pipenv
$ pipenv install --dev
```

Run the program:

```shell
$ python nanophotometer_sph.py
```

### Distribution

The program can be compiled into a portable executable with pyinstaller. Make sure that you are compiling on the same OS as the target system.

```shell
$ git clone https://github.com/olichen/nanophotometer_sph.git
$ cd /nanophotometer_sph
$ pip install pipenv
$ pipenv install --dev
$ pyinstaller --onefile --name nanophotometer_sph nanophotometer_sph.py
```

Windows users may need to install `pywin32-ctypes` and `pefile` to compile the project.

```shell
$ git clone https://github.com/olichen/nanophotometer_sph.git
$ cd /nanophotometer_sph
$ pip install pipenv
$ pipenv install --dev
$ pip install pywin32-ctypes pefile
$ pyinstaller --onefile --name nanophotometer_sph nanophotometer_sph.py
```

#### Debugging

`ImportError: DLL load failed while importing X`: Make sure that the operating system is fully updated. `pyinstaller` tries to hook into some system-specific libraries.

### Code

All the code is contained in one file: `nanophotometer_sph.py`. The code is broken into three classes: `NanophotometerNamespace`, `MySQLConnection`, and `CalcSPH`, and is initiated from the `main()` block. For further information, see the [source code](/nanophotometer_sph.py) or use the help() function from the python console.

```python
>>> import os
>>> os.chdir('/nanophotometer_sph')
>>> import nanophotometer_sph
>>> help(nanophotometer_sph)
```
