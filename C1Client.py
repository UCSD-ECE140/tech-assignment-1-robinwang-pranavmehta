import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import time
import random


# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    """
        Prints the result of the connection with a reasoncode to stdout ( used as callback for connect )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param flags: these are response flags sent by the broker
        :param rc: stands for reasonCode, which is a code for the connection result
        :param properties: can be used in MQTTv5, but is optional
    """
    print("CONNACK received with code %s." % rc)


# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    """
        Prints mid to stdout to reassure a successful publish ( used as callback for publish )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param properties: can be used in MQTTv5, but is optional
    """
    print("mid: " + str(mid))


# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """
        Prints a reassurance for successfully subscribing
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param granted_qos: this is the qos that you declare when subscribing, use the same one for publishing
        :param properties: can be used in MQTTv5, but is optional
    """
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


# print message, useful for checking if it was successful
def on_message(client, userdata, msg):
    """
        Prints a mqtt message to stdout ( used as callback for subscribe )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param msg: the message with topic and payload
    """

    print("message: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client1 = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Client_One", userdata=None, protocol=paho.MQTTv5)  #setup clients 1-3
    client1.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client1.connect(broker_address, broker_port)
    client1.on_subscribe = on_subscribe 
    client1.on_message = on_message
    client1.on_publish = on_publish 

    client2 = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Client_Two", userdata=None, protocol=paho.MQTTv5)
    client2.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client2.connect(broker_address, broker_port)
    client2.on_subscribe = on_subscribe 
    client2.on_message = on_message
    client2.on_publish = on_publish

    client3 = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Client_Three", userdata=None, protocol=paho.MQTTv5)
    client3.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client3.connect(broker_address, broker_port)
    client3.on_subscribe = on_subscribe 
    client3.on_message = on_message
    client3.on_publish = on_publish

    client3.subscribe("ece140brwpm/#")    #setup client 3 to listen
    
    client3.loop_start()
    while(True):
        try:
            client1.publish("ece140brwpm/1", json.dumps({'data':random.randrange(1,10,1)}))            #setup clients 1 and 2 to send data
            client2.publish("ece140brwpm/2", json.dumps({'data':random.randrange(1,10,1)}))
            time.sleep(3)
        except KeyboardInterrupt:
            break
    client3.loop_stop()
