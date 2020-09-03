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
        # print('message received', data)
        if 'ready' in data and data['ready'] == 'sample':
            response = requests.get(self.uri + '/rest/session/sample')
            # print(response.text)
            sql.update_database(response.text)


class MySQLConnection:
    def __init__(self, host: str, user: str, pw: str) -> None:
        db = 'etonbioscience'
        self._cnx = mysql.connector.connect(user=user, password=pw,
                                            host=host, database=db)
        self._cnx.close()

    def update_database(self, response: str):
        sample = json.loads(response)
        # print(sample)
        label = sample['label'].split()
        try:
            o_num = int(label[0])
            s_num = int(label[1])
            order_info = self._get_order_info(o_num, s_num)
            self._update_sample(o_num, s_num, sample, order_info)
        except Exception as e:
            print(e)
        except (IndexError, ValueError):
            print(f"Error finding order/sample: {sample['label']}")
        except mysql.connector.Error:
            print('Error connecting to database')

    def _get_order_info(self, o_num: int, s_num: int) -> dict:
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
        return data[0]

    def _update_sample(self, o_num: int, s_num: int, sample: dict, order: dict):
        # round the concentration and make sure it is as least 1
        conc = max(round(sample['c'], 0), 1)
        a260_a280 = round(sample['a260_a280'], 2)
        a260_a230 = round(sample['a260_a230'], 2)
        s, p, h = CalcSPH.calc_sph(conc, order)
        query = ("UPDATE sampletable "
                 f"SET measuredSampleCntr = '{conc}', "
                 f"S = '{s}', P = '{p}', H = '{h}', "
                 f"a260_a280 = '{a260_a280}', a260_a230 = '{a260_a230}' "
                 f"WHERE OrderNumber = '{o_num}' AND SampleID = '{s_num}'")

        self._cnx.reconnect()
        cursor = self._cnx.cursor()
        cursor.execute(query)
        print(f"Updated order {o_num:7d}, sample {s_num:2d} with "
              f"concentration = {conc:3.0f}, "
              f"S = {s:.1f}, P = {p:.1f}, H = {h:.1f}, "
              f"a260_a280 = {a260_a280:.2f}, a260_a230 = {a260_a230:.2f}. ")
        self._cnx.commit()
        cursor.close()
        self._cnx.close()


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
                    return CalcSPH._calc_sample_sph(conc, 'plas_spe', data['SampleSize'])
                return CalcSPH._calc_sample_sph(conc, 'plas_reg', data['SampleSize'])

            # PCR samples
            is_pcr = (data['DNAType'] == 'PCR' or data['SampleSize'][0:3] == 'PCR')
            is_purified = (data['purification'] == 'purified')
            if is_pcr and not is_purified:
                if is_purified:
                    return CalcSPH._calc_sample_sph(conc, 'pcr', data['SampleSize'])
                return (1.2, 1, 3)

    @staticmethod
    def _calc_sample_sph(self, conc: float, service: str, ssize: str) -> (float, float, float):
        base_vol = {}
        if service == 'plas_reg':
            base_vol = {'3': 110, '4': 115, '56': 125, '78': 140,
                        '910': 140, '1112': 140, '1315': 150, '1620': 155,
                        '2130': 160, '3150': 170, '50': 180}
        elif service == 'plas_spe':
            base_vol = {'3': 130, '4': 135, '56': 145, '78': 155,
                        '910': 155, '1112': 155, '1315': 160, '1620': 165,
                        '2130': 170, '3150': 175, '50': 175}
        elif service == 'pcr':
            base_vol = {'200': 5, '300': 5, '400': 8, '500': 10,
                        '1': 15, '15': 25, '23': 30, '4': 35,
                        '5': 35, '6': 50}

        # Strips non-numeric characters
        # ex: 'PCR - 300 bp' => '15', '1.5 kb' => '15'
        sample_size = ''.join(x for x in ssize if x.isdigit())
        S = round(base_vol[sample_size] / conc, 1)
        S = min(S, 4.0)
        S = max(S, 1.0)
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
