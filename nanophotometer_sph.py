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
            print(response.text)
            sql.update_database(response.text)

class MySQLConnection:
    def __init__(self, host: str, user: str, pw: str) -> None:
        self.host = host
        self.user = user
        self.pw = pw
        self.db = 'etonbioscience'
        cnx = mysql.connector.connect(user=self.user, password=self.pw,
                host=self.host, database=self.db)
        cnx.close()

    def update_database(self, data: str) -> bool:
        sample = json.loads(data)
        conc = round(sample['c'], 0)
        o_num = 960254 # test order
        s_num = 1
        select_query = ("SELECT ServiceType, DNAType, purification, "
                "isPurified, isSpecial, SampleSize, "
                "sampletable.Premixed AS s_pre, ordertable.Premixed AS o_pre "
                "FROM ordertable INNER JOIN sampletable "
                "ON ordertable.OrderNumber = sampletable.OrderNumber "
                f"WHERE ordertable.OrderNumber = '{o_num}' "
                f"AND SampleID = '{s_num}'")
        try:
            cnx = mysql.connector.connect(user=self.user, password=self.pw,
                    host=self.host, database=self.db)
        except mysql.connector.Error as e:
            print(e)
        else:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(select_query)
            for data in cursor:
                s, p, h = self.calc_sph(conc, data)
                update_query = ("UPDATE sampletable "
                    f"SET measuredSampleCntr = '{conc}', "
                    f"S = '{s}', P = '{p}', H = '{h}' "
                    f"WHERE OrderNumber = '{o_num}' AND SampleID = '{s_num}'")
                update_cursor = cnx.cursor()
                update_cursor.execute(update_query)
                print(f"Updated order {o_num}, sample {s_num} with "
                        f"concentration = {conc}, S = {s}, P = {p}, H = {h}.")
            cnx.close()

    def calc_sph(self, conc: float, data: dict) -> (int, int, int):
        if data['ServiceType'] == 'SeqDSC':
            return (1.5, 1, 3)
        if data['ServiceType'] == 'SeqReady2Load':
            return (99, 0, 0)
        if data['ServiceType'] == 'SeqRegular':
            # Premixed samples
            is_premixed = (data['o_pre'] == 'Y' or data['s_pre'] == 'Y')
            is_plasmid = (data['DNAType'] == 'Plasmid' or data['SampleSize'][0:7] == 'Plasmid')
            is_special = (data['isSpecial'] == 'yes')
            if is_premixed:
                if is_plasmid and is_special:
                    return (6, 0, 0)
                return (5, 0, 0)

            # Plasmid samples
            if is_plasmid:
                if is_special:
                    return self.calc_sph_service(conc, 'plas_spe', data['SampleSize'])
                return self.calc_sph_service(conc, 'plas_reg', data['SampleSize'])

            # PCR samples
            is_pcr = (data['DNAType'] == 'PCR' or data['SampleSize'][0:3] == 'PCR')
            is_purified = (data['purification'] == 'purified')
            if is_pcr and not is_purified:
                if is_purified:
                    return self.calc_sph_service(conc, 'pcr', data['SampleSize'])
                return (1.2, 1, 3)

    def calc_sph_service(self, conc: float, service: str, ssize: str) -> (int, int, int):
        base_vol = {}
        if service == 'plas_reg':
            base_vol = {'3': 110, '4': 115, '56': 125, '78': 140,
                    '910': 140, '1112': 140, '1315': 150, '1620': 155,
                    '2130': 160, '3150': 170, '50': 180}
        elif service == 'plas_spe':
            base_vol = {"3": 130, "4": 135, "56": 145, "78": 155,
                    "910": 155, "1112": 155, "1315": 160, "1620": 165,
                    "2130": 170, "3150": 175, "50": 175}
        elif service == 'pcr':
            base_vol = {"200": 5, "300": 5, "400": 8, "500": 10,
                    "1": 15, "15": 25, "23": 30, "4": 35,
                    "5": 35, "6": 50}

        # Strips non-numeric characters
        # ex: 'PCR - 300 bp' => '15', '1.5 kb' => '15'
        sample_size = ''.join(x for x in ssize if x.isdigit())
        S = round(base_vol[sample_size] / C, 1)
        H = 4 - (S // 1)
        return (S, 1, H)


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
