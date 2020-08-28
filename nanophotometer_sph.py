import socketio
import requests
import json
import mysql.connector
from getpass import getpass


class NanophotometerNamespace(socketio.ClientNamespace):
    def __init__(self, uri, sql) -> None:
        super().__init__()
        self.uri = uri
        self.sql = sql

    def on_connect(self) -> None:
        print('connected')

    def on_connection_error(self) -> None:
        print('connection error')

    def on_disconnect(self) -> None:
        print('disconnected')

    def on_message(self, data: dict):
        print('message received', data)
        if 'ready' in data and data['ready'] == 'sample':
            response = requests.get(self.uri + '/rest/session/sample')
            sql.updateDatabase(response.text)
            print(response.text)

class MySQLConnection:
    def __init__(self, host: str, user: str, pw: str) -> None:
        self.host = host
        self.user = user
        self.pw = pw
        self.db = 'etonbioscience'
        cnx = mysql.connector.connect(user=self.user, password=self.pw,
                host=self.host, database=self.db)
        cnx.close()

    def updateDatabase(self, data: str) -> bool:
        sample = json.loads(data)
        conc = sample['c']
        s = conc + 1
        p = conc + 2
        h = conc + 3
        o_num = 960254 # test order
        s_num = 1
        try:
            cnx = mysql.connector.connect(user=self.user, password=self.pw,
                    host=self.host, database=self.db)
        except mysql.connector.Error as e:
            print(e)
        else:
            cursor = cnx.cursor()
            query = ("UPDATE sampletable "
                    f"SET SampleCntr = '{conc}', S = '{s}', P = '{p}', H = '{h}' "
                    f"WHERE OrderNumber = '{o_num}' AND SampleID = '{s_num}'")
            print(query)
            cursor.execute(query)
            cnx.close()

if __name__ == '__main__':
    host = input('SQL server host > ')
    user = input('username > ')
    pw = getpass('password > ')
    sql = MySQLConnection(host, user, pw)

    ip = input('Nanophotometer ip address > ')
    ip = ip or '192.168.1.31'
    uri = 'http://' + ip
    sio = socketio.Client()

    sio.register_namespace(NanophotometerNamespace(uri, sql))
    sio.connect(uri + ':8765')

    sio.wait()
