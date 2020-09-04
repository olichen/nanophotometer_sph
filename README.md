# Nanophotometer SPH

> Initiates a socket.io connection to an Implen Nanophotometer, parses sample data, and updates the Eton database

---

## Usage

1. Update the database connection so it automatically logs in
2. Type in the IP address of the Nanophotometer to connect to

---

## Development

### Setup

#### Windows

1. Install [Python](https://www.python.org/). During Python setup, make sure that you add Python to your PATH.
2. Install a [git client](https://git-scm.com/).
3. Open up Git Bash in the folder you'd like to install the program.
4. Go to "Bash" section below.

#### Bash

Clone the respository and go into the created folder:

```shell
$ git clone https://github.com/olichen/nanophotometer_sph.git
$ cd /nanophotometer_sph
```

Use Python's package manager to set up a virtual environment with all the required packages:

```shell
$ pip install pipenv
$ pipenv install --dev
```

Run the program:

```shell
$ python nanophotometer_sph.py
```

### Distribution

The program can be compiled into a portable executable with pyinstaller. Make sure that you are compiling on the same OS as the target system. Windows users need to install `pywin32-ctypes`.

```shell
$ git clone https://github.com/olichen/nanophotometer_sph.git
$ cd /nanophotometer_sph
$ pip install pipenv
$ pipenv install --dev
$ pyinstaller --onefile --name nanophotometer_sph nanophotometer_sph.py
```

#### Debugging

`ImportError: DLL load failed while importing X`: Make sure that the operating system is fully updated. Python tries to hook into some system-specific libraries.

### Coding
