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

```python
class NanophotometerNamespace(socketio.namespace.ClientNamespace)
     |  NanophotometerNamespace(uri: str, sql) -> None
     |
     |  A client-side class-based namespace for the socketio client.
     |
     |  Creates the event handlers for the connection to the nanophotometer.
     |
     |  __init__(self, uri: str, sql) -> None
     |      NanophotometerNamespace object constructor.
     |
     |      :param uri: URI of the nanophotometer.
     |      :param sql: MySQLConnection object that connects to the database.
     |
     |  on_connect(self) -> None
     |      Prints a message on connection to the nanophotometer.
     |
     |  on_connection_error(self) -> None
     |      Prints a message on error connecting to the nanophotometer.
     |
     |  on_disconnect(self) -> None
     |      Prints a message on disconnect from the nanophotometer.
     |
     |  on_message(self, data: dict) -> None
     |      Triggered when a message is received from the nanophotometer.
     |
     |      If the message indicates that a sample is ready, retrieves the sample
     |      data with a GET request to the nanophotometer. The text from the
     |      response is sent to the MySQLConnection object to update the database.
     |
     |      :param data: Message received from the nanophotometer.

class MySQLConnection(builtins.object)
     |  MySQLConnection(host: str, user: str, pw: str, db: str) -> None
     |
     |  Connects to and queries the SQL database.
     |
     |  __init__(self, host: str, user: str, pw: str, db: str) -> None
     |      MySQLConnection object constructor. Opens a connection to the MySQL
     |      server.
     |
     |      :param host: Host name or IP address of the MySQL Server.
     |      :param user: The user name used to authenticate with the server.
     |      :param pw: The password used to authenticate the user with the server.
     |      :param db: The database name to use when connecting to the server.
     |
     |  select_order_data(self, o_num: int, s_num: int) -> dict
     |      Queries ordertable/sampletable for information needed to calculate SPH.
     |
     |      :param o_num: Order number.
     |      :param s_num: Sample ID.
     |
     |  update_database(self, response: str) -> None
     |      Parses the sample data received from the nanophotometer for the order
     |      number and sample id to update, queries the database for information
     |      needed to calculate SPH, calculates SPH, then updates the database.
     |
     |      :param response: The sample data received from the nanophotometer.
     |
     |  update_sampletable(self, o_num: int, s_num: int, **kwargs) -> None
     |      Updates the sampletable with the values provided.
     |
     |      :param o_num: Order number of the sample to be updated.
     |      :param s_num: Sample ID of the sample to be updated.
     |      :param **kwargs: Columns of the database to be updated.

class CalcSPH(builtins.object)
     |  Calculates and returns SPH values.
     |
     |  calc_sph(conc: float, data: dict) -> (<class 'float'>, <class 'float'>, <class 'float'>)
     |      Calculates and returns SPH.
     |
     |      :param conc: Measured concentration of the sample.
     |      :param data: Order data received from select_order_data().
```

#### Workflow

* `__main__`: Initiates a `MySQLConnection` to the database. The database connection and nanophotometer URI are passed to a `NanophotometerNamespace`, a socketio event handler. The event handler is registered to a socketio client, which connects to the nanophotometer on the URI provided.
* `NanophotometerNamespace`: When a message is received, the data is sent to `NanophotometerNamespace.on_message()`. If the message indicates that a sample is ready, we retrieve the sample data with a GET request to the nanophotometer. The text from the response is sent to `MySQLConnection.update_database()`.
* `MySQLConnection.update_database()`: Parses the sample data received, queries the database for information needed to calculate SPH, calculates SPH, then updates the database.
  * First, it loads the received data into a JSON object and tries to parse the sample name for the order number and sample id.
  * If we are able to parse the order number and sample id, we pass the values to `MySQLConnection._select()` to retrieve the order information necessary to calculate SPH.
  * The data retrieved is passed to `CalcSPH.calc_sph` to calculate the SPH.
  * Concentration, SPH, and other values to be updated are passed to `MySQLConnection._update()` to update the database.
