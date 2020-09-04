import socketio
import requests
import json
import mysql.connector
from getpass import getpass


# Namespace for the nanophotometer
class NanophotometerNamespace(socketio.ClientNamespace):
    def __init__(self, uri, sql) -> None:
        super().__init__()
        self._uri = uri
        self._sql = sql

    def on_connect(self) -> None:
        print(f'Connected to nanophotometer on {self._uri}')

    def on_connection_error(self) -> None:
        print('Error connecting to nanophotometer')

    def on_disconnect(self) -> None:
        print('Disconnected from nanophotometer')

    # When a message is received
    def on_message(self, data: dict):
        # If message contains {'ready': 'sample'}
        if 'ready' in data and data['ready'] == 'sample':
            # GET request to the nanophotometer
            response = requests.get(self._uri + '/rest/session/sample')
            # Try to update the database
            self._sql.update_database(response.text)


# Connects to the SQL database and updates the samples
class MySQLConnection:
    def __init__(self, host: str, user: str, pw: str) -> None:
        # Initiate and close the connection
        db = 'etonbioscience'
        self._cnx = mysql.connector.connect(user=user, password=pw,
                                            host=host, database=db)
        self._cnx.close()

    # Try to update the database
    def update_database(self, response: str):
        sample = json.loads(response)
        try:
            # Split label into two ints: order_number and sample_number
            # Raises IndexError or ValueError unable to split into ints
            label = sample['label'].split()
            o_num = int(label[0])
            s_num = int(label[1])

            # Get data needed to calculate SPH
            order_info = self._select(o_num, s_num)
            # Insert concentration and SPH into the database
            self._update(o_num, s_num, sample, order_info)
        except (IndexError, ValueError):
            print(f"Error finding order/sample: {sample['label']}")
        except mysql.connector.Error:
            print('Error connecting to database')

    # Queries the database for info needed to calculate SPH
    def _select(self, o_num: int, s_num: int) -> dict:
        query = ("SELECT ServiceType, DNAType, purification, "
                 "isPurified, isSpecial, SampleSize, "
                 "sampletable.Premixed AS s_pre, ordertable.Premixed AS o_pre "
                 "FROM ordertable INNER JOIN sampletable "
                 "ON ordertable.OrderNumber = sampletable.OrderNumber "
                 f"WHERE ordertable.OrderNumber = '{o_num}' "
                 f"AND SampleID = '{s_num}'")
        self._cnx.reconnect()
        cursor = self._cnx.cursor(dictionary=True)
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        self._cnx.close()
        # Returns first row found, or raises IndexError if nothing is found
        return data[0]

    # Updates the sampletable
    def _update(self, o_num: int, s_num: int, s_data: dict, o_data: dict) -> None:
        # Round the concentration and make sure it is as least 1
        conc = max(round(s_data['c'], 0), 1)
        s, p, h = CalcSPH.calc_sph(conc, o_data)
        a260_a280 = round(s_data['a260_a280'], 2)
        a260_a230 = round(s_data['a260_a230'], 2)
        query = ("UPDATE sampletable "
                 f"SET measuredSampleCntr = '{conc}', "
                 f"S = '{s}', P = '{p}', H = '{h}', "
                 f"a260_a280 = '{a260_a280}', a260_a230 = '{a260_a230}' "
                 f"WHERE OrderNumber = '{o_num}' AND SampleID = '{s_num}'")

        self._cnx.reconnect()
        cursor = self._cnx.cursor()
        cursor.execute(query)
        self._cnx.commit()
        cursor.close()
        self._cnx.close()
        print(f"Updated order {o_num:7d}, sample {s_num:2d} with "
              f"concentration = {conc:3.0f}, "
              f"S = {s:.1f}, P = {p:.1f}, H = {h:.1f}, "
              f"a260_a280 = {a260_a280:.2f}, a260_a230 = {a260_a230:.2f}. ")


# Calculates SPH. 'data' is the order data returned by the SELECT statement in
# MySqlConnection._select
class CalcSPH:
    @staticmethod
    def calc_sph(conc: float, data: dict) -> (float, float, float):
        if data['ServiceType'] == 'SeqDSC':
            return (1.5, 1, 3)
        if data['ServiceType'] == 'SeqReady2Load':
            return (99, 0, 0)
        if data['ServiceType'] == 'SeqRegular':
            # Premixed samples
            is_premixed = (data['o_pre'] == 'Y' or data['s_pre'] == 'Y')
            is_plasmid = (data['DNAType'] == 'Plasmid'
                          or data['SampleSize'][0:7] == 'Plasmid')
            is_special = (data['isSpecial'] == 'yes')
            if is_premixed:
                if is_plasmid and is_special:
                    return (6, 0, 0)
                return (5, 0, 0)

            # Plasmid samples
            if is_plasmid:
                if is_special:
                    return CalcSPH._sample(conc, 'p_spe', data['SampleSize'])
                return CalcSPH._sample(conc, 'p_reg', data['SampleSize'])

            # PCR samples
            is_pcr = (data['DNAType'] == 'PCR'
                      or data['SampleSize'][0:3] == 'PCR')
            is_purified = (data['purification'] == 'purified')
            if is_pcr and not is_purified:
                if is_purified:
                    return CalcSPH._sample(conc, 'pcr', data['SampleSize'])
                return (1.2, 1, 3)

    @staticmethod
    def _sample(self, conc: float, service: str, ssize: str) \
            -> (float, float, float):
        base_vol = {}
        if service == 'p_reg':
            base_vol = {'3': 110, '4': 115, '56': 125, '78': 140,
                        '910': 140, '1112': 140, '1315': 150, '1620': 155,
                        '2130': 160, '3150': 170, '50': 180}
        elif service == 'p_spe':
            base_vol = {'3': 130, '4': 135, '56': 145, '78': 155,
                        '910': 155, '1112': 155, '1315': 160, '1620': 165,
                        '2130': 170, '3150': 175, '50': 175}
        elif service == 'pcr':
            base_vol = {'200': 5, '300': 5, '400': 8, '500': 10,
                        '1': 15, '15': 25, '23': 30, '4': 35,
                        '5': 35, '6': 50}

        # Strips non-numeric characters
        # ex: 'PCR - 300 bp' => '300', '1.5 kb' => '15'
        sample_size = ''.join(x for x in ssize if x.isdigit())

        # Round S to the nearest .1, and make sure 1 <= S <= 4
        S = round(base_vol[sample_size] / conc, 1)
        S = max(min(S, 4), 1)

        # H set to 4 - FLOOR(S)
        H = 4 - (S // 1)
        return (S, 1, H)


if __name__ == '__main__':
    # Connect to the database
    host = input('SQL server host > ')
    user = input('username > ')
    pw = getpass('password > ')
    sql = MySQLConnection(host, user, pw)

    # Connect to the Nanophotometer and wait
    ip = input('Nanophotometer ip address > ')
    ip = ip or '192.168.1.31'
    uri = 'http://' + ip
    sio = socketio.Client()
    sio.register_namespace(NanophotometerNamespace(uri, sql))
    sio.connect(uri + ':8765')
    sio.wait()
