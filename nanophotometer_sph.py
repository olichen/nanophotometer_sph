import socketio
import requests
import json
import mysql.connector
from getpass import getpass


class NanophotometerNamespace(socketio.ClientNamespace):
    '''
    A client-side class-based namespace for the socketio client.

    Creates the event handlers for the connection to the nanophotometer.
    '''
    def __init__(self, uri: str, sql) -> None:
        '''
        NanophotometerNamespace object constructor.

        :param uri: URI of the nanophotometer.
        :param sql: MySQLConnection object that connects to the database.
        '''
        super().__init__()
        self._uri = uri
        self._sql = sql

    def on_connect(self) -> None:
        '''Prints a message on connection to the nanophotometer.'''
        print(f'Connected to nanophotometer on {self._uri}')

    def on_connection_error(self) -> None:
        '''Prints a message on error connecting to the nanophotometer.'''
        print('Error connecting to nanophotometer')

    def on_disconnect(self) -> None:
        '''Prints a message on disconnect from the nanophotometer.'''
        print('Disconnected from nanophotometer')

    def on_message(self, data: dict) -> None:
        '''
        Triggered when a message is received from the nanophotometer.

        If the message indicates that a sample is ready, retrieves the sample
        data with a GET request to the nanophotometer. The text from the
        response is sent to the MySQLConnection object to update the database.

        :param data: Message received from the nanophotometer.
        '''
        if 'ready' in data and data['ready'] == 'sample':
            response = requests.get(self._uri + '/rest/session/sample')
            self._sql.update_database(response.text)


class MySQLConnection:
    '''Connects to and queries the SQL database.'''
    def __init__(self, host: str, user: str, pw: str, db: str) -> None:
        # Initiate and close the connection
        '''
        MySQLConnection object constructor. Opens a connection to the MySQL
        server.

        :param host: Host name or IP address of the MySQL Server.
        :param user: The user name used to authenticate with the server.
        :param pw: The password used to authenticate the user with the server.
        :param db: The database name to use when connecting to the server.
        '''
        self._cnx = mysql.connector.connect(user=user, password=pw,
                                            host=host, database=db)
        self._cnx.close()

    def update_database(self, response: str) -> None:
        '''
        Parses the sample data received from the nanophotometer for the order
        number and sample id to update, queries the database for information
        needed to calculate SPH, calculates SPH, then updates the database.

        :param response: The sample data received from the nanophotometer.
        '''
        s_data = json.loads(response)
        try:
            # Try to parse order number and sample id from the sample data
            # Raises IndexError or ValueError if unable to parse
            label = s_data['label'].split()
            o_num = int(label[0])
            s_num = int(label[1])

            # Get data needed to calculate SPH
            o_data = self.select_order_data(o_num, s_num)

            # Get concentration, S, P, H, A260/A280, and A260/A230
            conc = max(round(s_data.get('c', 1), 0), 1)
            s, p, h = CalcSPH.calc_sph(conc, o_data)
            a260_a280 = round(s_data.get('a260_a280', 0), 2)
            a260_a230 = round(s_data.get('a260_a230', 0), 2)

            # Insert concentration and SPH into the database
            self.update_sampletable(o_num=o_num, s_num=s_num,
                                    measuredSampleCntr=conc, S=s, P=p, H=h,
                                    a260_a280=a260_a280, a260_a230=a260_a230)
            print(f"Updated order {o_num:7d}, sample {s_num:2d} with "
                  f"concentration = {conc:3.0f}, "
                  f"S = {s:.1f}, P = {p:.1f}, H = {h:.1f}, "
                  f"a260_a280 = {a260_a280:.2f}, a260_a230 = {a260_a230:.2f}")
        except (IndexError, ValueError):
            print(f"Error finding order/sample: {s_data['label']}")
        except mysql.connector.Error:
            print('Error connecting to database')

    def select_order_data(self, o_num: int, s_num: int) -> dict:
        '''
        Queries ordertable/sampletable for information needed to calculate SPH.

        :param o_num: Order number.
        :param s_num: Sample ID.
        '''
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

    def update_sampletable(self, o_num: int, s_num: int, **kwargs) -> None:
        '''
        Updates the sampletable with the values provided.

        :param o_num: Order number of the sample to be updated.
        :param s_num: Sample ID of the sample to be updated.
        :param **kwargs: Columns of the database to be updated.
        '''
        cols_to_update = []
        for key, value in kwargs.items():
            cols_to_update.append(f"{key} = '{value}'")
        query = ("UPDATE sampletable SET " + ", ".join(cols_to_update) + " "
                 f"WHERE OrderNumber = '{o_num}' AND SampleID = '{s_num}'")
        self._cnx.reconnect()
        cursor = self._cnx.cursor()
        cursor.execute(query)
        self._cnx.commit()
        cursor.close()
        self._cnx.close()


class CalcSPH:
    '''Calculates and returns SPH values.'''
    @staticmethod
    def calc_sph(conc: float, data: dict) -> (float, float, float):
        '''
        Calculates and returns SPH.

        :param conc: Measured concentration of the sample.
        :param data: Order data received from select_order_data().
        '''
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
    def _sample(conc: float, service: str, size: str) -> (float, float, float):
        '''
        Calculates and returns SPH.

        :param conc: Measured concentration of the sample.
        :param service: Service type; plasmid/pcr regular/special.
        :param size: SampleSize field from sampletable.
        '''
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
        sample_size = ''.join(x for x in size if x.isdigit())

        # Round S to the nearest .1, and make sure 1 <= S <= 4
        S = round(base_vol[sample_size] / conc, 1)
        S = max(min(S, 4), 1)

        # H set to 4 - FLOOR(S)
        H = 4 - (S // 1)
        return (S, 1, H)

def main():
    '''
    Initiates a socketio connection to the nanophotometer. An SQL connection
    object is passed to the namespace when it is created.
    '''
    # Connect to the database
    host = input('SQL server host > ')
    user = input('username > ')
    pw = getpass('password > ')
    db = 'etonbioscience'
    sql = MySQLConnection(host, user, pw, db)

    # Connect to the Nanophotometer and wait
    ip = input('Nanophotometer ip address > ')
    ip = ip or '192.168.1.31'
    uri = 'http://' + ip
    sio = socketio.Client()
    sio.register_namespace(NanophotometerNamespace(uri, sql))
    sio.connect(uri + ':8765')
    sio.wait()

if __name__ == '__main__':
    main()
