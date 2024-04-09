import os
import json
import random
import math
import time
import paho.mqtt.client as paho
from dotenv import load_dotenv

# Callbacks for MQTT events
def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_publish(client, userdata, mid, properties=None):
    print("mid: " + str(mid))

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_message(client, userdata, msg):
    global exit, exit_reason, scores, move_flag, player_data
    player_id = msg.topic.split("/")[-2]  # Extract player ID from the topic
    if msg.topic == f"games/{lobby_name}/lobby":
        exit = 1
        exit_reason = json.loads(msg.payload)
    elif msg.topic == f"games/{lobby_name}/scores":
        scores = json.loads(msg.payload)
    elif msg.topic.startswith(f"games/{lobby_name}/player_") and msg.topic.endswith("/game_state"):
        player_data[player_id] = json.loads(msg.payload)
        move_flag += 1

def determine_best_target(player_data, player_id):
    pos = player_data["currentPosition"]
    coins = player_data["coin1"] + player_data["coin2"] + player_data["coin3"]
    print("coins")
    print(coins)
    if coins:
        player_target = player_targets[player_id]
        if player_target is not None and player_target in coins:
            return player_target

        target = min(coins, key=lambda coin: math.sqrt((coin[0] - pos[0]) ** 2 + (coin[1] - pos[1]) ** 2))
        player_targets[player_id] = target
        return target
    else:
        return None

def determine_next_move(player_data, player_id):
    target = determine_best_target(player_data, player_id)
    if target is not None:
        pos = player_data["currentPosition"]
        print(player_id)
        print(pos)
        obstacles = player_data["enemyPositions"] + player_data["teammatePositions"] + player_data["walls"]  #remember coordinates given in y,x pairs
        x_obstacles = set((obstacle[1], obstacle[0]) for obstacle in obstacles if obstacle[0] == pos[0])
        y_obstacles = set((obstacle[1], obstacle[0]) for obstacle in obstacles if obstacle[1] == pos[1])
        x_diff = target[1] - pos[1]
        y_diff = target[0] - pos[0]

        if x_diff > 0 and (pos[1] + 1, pos[0]) not in x_obstacles and (pos[1] + 1) < 10:
            print("R")
            return "RIGHT"
        elif x_diff < 0 and (pos[1] - 1, pos[0]) not in x_obstacles and (pos[1] - 1) >= 0:
            print("L")
            return "LEFT"
        elif y_diff > 0 and (pos[1], pos[0] + 1) not in y_obstacles and (pos[0] + 1) < 10:
            print("D")
            return "DOWN"
        elif y_diff < 0 and (pos[1], pos[0] - 1) not in y_obstacles and (pos[0] - 1) >= 0:
            print("U")
            return "UP"
    return random.choice(["UP", "DOWN", "LEFT", "RIGHT"])

if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Player1", userdata=None, protocol=paho.MQTTv5)
    client.tls_set(tls_version=paho.ssl.PROTOCOL_TLS)
    client.connect(broker_address, broker_port)

    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_publish = on_publish

    lobby_name = input("Please enter lobby name: ")
    client.subscribe(f"games/{lobby_name}/lobby")
    for i in range(1, 5):
        client.subscribe(f"games/{lobby_name}/player_{i}/game_state")

    client.subscribe(f"games/{lobby_name}/scores")

    # Initialize player data and targets
    player_data = {f"player_{i}": None for i in range(1, 5)}
    player_targets = {f"player_{i}": None for i in range(1, 5)}

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

    # Start the game
    start_game = input("Start game? Please enter y: ")
    if start_game == "y":
        client.publish(f"games/{lobby_name}/start", "START")

    move_flag = 0
    client.loop_start()

    while True:
        try:
            if exit == 1:
                print(exit_reason)
                client.publish(f"games/{lobby_name}/start", "STOP")
                break

            while move_flag < 4:
                time.sleep(0.1)
            move_flag = 0
            for i in range(1, 5):
                player_id = f"player_{i}"
                move = determine_next_move(player_data[player_id], player_id)
                client.publish(f"games/{lobby_name}/{player_id}/move", move)
                time.sleep(3)

        except KeyboardInterrupt:
            client.publish(f"games/{lobby_name}/start", "STOP")
            break

    client.loop_stop()