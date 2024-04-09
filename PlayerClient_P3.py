import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import time
import random
import math

global exit, exit_reason, scores, lobby_name, player_1_name, player_2_name, player_3_name, player_4_name, move_flag, p1_data, p2_data, p3_data, p4_data
exit = 0
exit_reason = None
scores = None

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
    global exit, exit_reason, scores, move_flag, p1_data, p2_data, p3_data, p4_data
    if msg.topic == f"games/{lobby_name}/lobby":
        exit = 1
        exit_reason = json.loads(msg.payload)
    elif msg.topic == f"games/{lobby_name}/scores":
        scores = json.loads(msg.payload)
    elif msg.topic == f"games/{lobby_name}/player_1/game_state":
        p1_data = json.loads(msg.payload)
        move_flag += 1
    elif msg.topic == f"games/{lobby_name}/player_2/game_state":
        p2_data = json.loads(msg.payload)
        move_flag += 1
    elif msg.topic == f"games/{lobby_name}/player_3/game_state":
        p3_data = json.loads(msg.payload)
        move_flag += 1
    elif msg.topic == f"games/{lobby_name}/player_4/game_state":
        p4_data = json.loads(msg.payload)
        move_flag += 1

def determine_best_target(player_data):
    try:
        coins = player_data["coin1"] + player_data["coin2"] + player_data["coin3"]
        if coins:
            target = coins[0]
            target_cost = math.sqrt(math.pow(target[0],2) + math.pow(target[1],2))
            for coin in player_data["coin1"]:
                cost = math.sqrt(math.pow(target[0],2) + math.pow(target[1],2))
                if cost < target_cost:
                    target = coin
                    target_cost = cost

            for coin in player_data["coin2"]:
                cost = math.sqrt(math.pow(target[0],2) + math.pow(target[1],2)) - 1   #weighing more valuable coin more
                if cost < target_cost:
                    target = coin
                    target_cost = cost

            for coin in player_data["coin3"]:
                cost = math.sqrt(math.pow(target[0],2) + math.pow(target[1],2)) - 2  #weighing more valuable coin more
                if cost < target_cost:
                    target = coin
                    target_cost = cost

            return target
        else:
            return None
    except Exception as e:
        print(e)

def determine_next_move(player_data):
    try:
        pos = player_data["currentPosition"]
        target = determine_best_target(player_data)
        obstacles = player_data["enemyPositions"] + player_data["teammatePositions"] + player_data["walls"]

        if target is not None:
            x_obstacles = []
            y_obstacles = []
            for obstacle in obstacles:
                x_obstacles.append(obstacle[0])
                y_obstacles.append(obstacle[1])

            x_diff = target[0] - pos[0]
            y_diff = target[0] - pos[0]

            if (abs(x_diff) >= abs(y_diff)):
                if (x_diff > 0):
                    new_x = pos[0] + 1
                    if new_x not in x_obstacles:
                        return "RIGHT"

                elif (x_diff < 0):
                    new_x = pos[0] - 1
                    if new_x not in x_obstacles:
                        return "LEFT"
                
                new_y_1 = pos[1] + 1
                new_y_2 = pos[1] - 1
                if new_y_1 not in y_obstacles:
                    return "UP"
                if new_y_2 not in y_obstacles:
                    return "DOWN"
                
            elif (abs(x_diff) < abs(y_diff)):
                if (y_diff > 0):
                    new_y = pos[1] + 1
                    if new_y not in y_obstacles:
                       return "UP"
                elif (y_diff < 0):
                    new_y = pos[1] - 1
                    if new_y not in y_obstacles:
                        return "DOWN"
                
                new_x_1 = pos[0] + 1
                new_x_2 = pos[0] - 1
                if new_x_1 not in x_obstacles:
                    return "RIGHT"
                if new_x_2 not in x_obstacles:
                    return "LEFT"
                
        return match_move(random.randrange(1,5))
    except Exception as e:
        print(e)

def match_move(move):
    match(move):
        case 1:
            return "UP"
        case 2:
            return "DOWN"
        case 3:
            return "LEFT"
        case 4:
            return "RIGHT"

if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Player1", userdata=None, protocol=paho.MQTTv5)
    
    # enable TLS for secure connection
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # set username and password
    #client.username_pw_set(username, password)  #comment out for now
    # connect to HiveMQ Cloud on port 8883 (default for MQTT)
    client.connect(broker_address, broker_port)

    # setting callbacks, use separate functions like above for better visibility
    client.on_subscribe = on_subscribe # Can comment out to not print when subscribing to new topics
    client.on_message = on_message
    client.on_publish = on_publish # Can comment out to not print when publishing to topics

    lobby_name = input("Please enter lobby name: ")
    #player_1_name = input("Please enter name for player 1: ")
    #player_2_name = input("Please enter name for player 2: ")
    #player_3_name = input("Please enter name for player 3: ")
    #player_4_name = input("Please enter name for player 4: ")

    client.subscribe(f"games/{lobby_name}/lobby")
    client.subscribe(f'games/{lobby_name}/+/game_state')
    client.subscribe(f'games/{lobby_name}/scores')

    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'ATeam',
                                            'player_name' : 'player_1'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'ATeam',
                                            'player_name' : 'player_2'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                        'team_name':'BTeam',
                                        'player_name' : 'player_3'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                        'team_name':'BTeam',
                                        'player_name' : 'player_4'}))

    
    time.sleep(1) # Wait a second to resolve game start

    while True:
        start_game = input("Start game? Please enter y or n: ")
        if start_game == "y":
            client.publish(f"games/{lobby_name}/start", "START")
            break
        elif start_game == "n":
            break
        else:
            print("Please enter y or n.")

    client.loop_start()   
    
    i = 0
    move_flag = 0
    player_1_move = match_move(random.randrange(1,5))
    player_2_move = match_move(random.randrange(1,5))
    player_3_move = match_move(random.randrange(1,5))
    player_4_move = match_move(random.randrange(1,5))
    while (True):
        try:
            if exit == 1:
                print(exit_reason)
                client.publish(f"games/{lobby_name}/start", "STOP")
                break

            move_flag = 0
            if player_1_move is not None: client.publish(f"games/{lobby_name}/player_1/move", player_1_move)
            time.sleep(3)
            if player_2_move is not None: client.publish(f"games/{lobby_name}/player_2/move", player_2_move)
            time.sleep(3)
            if player_3_move is not None: client.publish(f"games/{lobby_name}/player_3/move", player_3_move)
            time.sleep(3)
            if player_4_move is not None: client.publish(f"games/{lobby_name}/player_4/move", player_4_move)
            time.sleep(3)
            while(move_flag < 4): time.sleep(0.1)
            player_1_move = determine_next_move(p1_data)
            player_2_move = determine_next_move(p2_data)
            player_3_move = determine_next_move(p3_data)
            player_4_move = determine_next_move(p4_data)
            """
            while True:
                player_input = input("Please use wasd to move: ")
                if player_input in ['w', 'a', 's', 'd']:
                    if player_input == "w":
                        client.publish(f"games/{lobby_name}/player_1/move", "UP")
                    elif player_input == "a":
                        client.publish(f"games/{lobby_name}/player_1/move", "LEFT")
                    elif player_input == "s":
                        client.publish(f"games/{lobby_name}/player_1/move", "DOWN")
                    elif player_input == "d":
                        client.publish(f"games/{lobby_name}/player_1/move", "RIGHT")
                    break
                else:
                    print("Invalid input! Please enter either 'w', 'a', 's', or 'd'.")
            while True:
                player_input = input("Please use wasd to move: ")
                if player_input in ['w', 'a', 's', 'd']:
                    if player_input == "w":
                        client.publish(f"games/{lobby_name}/player_2/move", "UP")
                    elif player_input == "a":
                        client.publish(f"games/{lobby_name}/player_2/move", "LEFT")
                    elif player_input == "s":
                        client.publish(f"games/{lobby_name}/player_2/move", "DOWN")
                    elif player_input == "d":
                        client.publish(f"games/{lobby_name}/player_2/move", "RIGHT")
                    break
                else:
                    print("Invalid input! Please enter either 'w', 'a', 's', or 'd'.")
            while True:
                player_input = input("Please use wasd to move: ")
                if player_input in ['w', 'a', 's', 'd']:
                    if player_input == "w":
                        client.publish(f"games/{lobby_name}/player_3/move", "UP")
                    elif player_input == "a":
                        client.publish(f"games/{lobby_name}/player_3/move", "LEFT")
                    elif player_input == "s":
                        client.publish(f"games/{lobby_name}/player_3/move", "DOWN")
                    elif player_input == "d":
                        client.publish(f"games/{lobby_name}/player_3/move", "RIGHT")
                    break
                else:
                    print("Invalid input! Please enter either 'w', 'a', 's', or 'd'.")
            while True:
                player_input = input("Please use wasd to move: ")
                if player_input in ['w', 'a', 's', 'd']:
                    if player_input == "w":
                        client.publish(f"games/{lobby_name}/player_4/move", "UP")
                    elif player_input == "a":
                        client.publish(f"games/{lobby_name}/player_4/move", "LEFT")
                    elif player_input == "s":
                        client.publish(f"games/{lobby_name}/player_4/move", "DOWN")
                    elif player_input == "d":
                        client.publish(f"games/{lobby_name}/player_4/move", "RIGHT")
                    break
                else:
                    print("Invalid input! Please enter either 'w', 'a', 's', or 'd'.")
            """

        except KeyboardInterrupt:
            client.publish(f"games/{lobby_name}/start", "STOP")
            break

        except Exception as e:
            print(e)

    client.loop_stop()
    