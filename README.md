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

All the code is contained in one file: `nanophotometer_sph.py`. The code is broken into three classes: `NanophotometerNamespace`, `MySQLConnection`, and `CalcSPH`.

`NanophotometerNamespace`: Creates the event handlers for the socketio client. `on_message(data)` is called when a message is received from the nanophotometer via the socketio connection.

`MySQLConnection`: Logs into and queries the SQL database

`CalcSPH`: Calculates SPH from the given concentration and order information

#### Workflow

* `__main__`: Initiates a `MySQLConnection` to the database. The database connection and nanophotometer URI are passed to a `NanophotometerNamespace`, a socketio event handler. The event handler is registered to a socketio client, which connects to the nanophotometer on the URI provided.
* `NanophotometerNamespace`: When a message is received, the data is sent to `NanophotometerNamespace.on_message()`. If the message indicates that a sample is ready, we retrieve the sample data with a GET request to the nanophotometer. The text from the response is sent to `MySQLConnection.update_database()`.
* `MySQLConnection.update_database()`: Parses the sample data received, queries the database for information needed to calculate SPH, calculates SPH, then updates the database.
  * First, it loads the received data into a JSON object and tries to parse the sample name for the order number and sample id.
  * If we are able to parse the order number and sample id, we pass the values to `MySQLConnection._select()` to retrieve the order information necessary to calculate SPH.
  * The data retrieved is passed to `CalcSPH.calc_sph` to calculate the SPH.
  * Concentration, SPH, and other values to be updated are passed to `MySQLConnection._update()` to update the database.
