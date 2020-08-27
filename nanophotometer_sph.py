import socketio
import requests
import json

sio = socketio.Client()
uri = 'http://192.168.1.31'

@sio.event
def connect():
    print('connected')

@sio.event
def message(data):
    print('message received', data)
    if 'ready' in data and data['ready'] == 'sample':
        response = requests.get(uri + '/rest/session/sample')
        print(response.text)

@sio.event
def disconnect():
    print('disconnected')

sio.connect(uri + ':8765')
sio.wait()
