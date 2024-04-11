import os
import json
import random
import math
import time
import paho.mqtt.client as paho
from dotenv import load_dotenv

DEFAULT_CHOICE = "UP"

global exit, exit_reason, scores, lobby_name, player_name, team_name
exit = 0
exit_reason = None
scores = None

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
    if msg.topic == f"games/{lobby_name}/lobby":  #Exits when lobby state changes - either error or game over
        exit = 1
        exit_reason = str(msg.payload)
    elif msg.topic == f"games/{lobby_name}/scores":   #Gets the scores
        scores = json.loads(msg.payload)
    elif msg.topic.startswith(f"games/{lobby_name}/ply") and msg.topic.endswith("/game_state"):  #Gets feedback for player moves
        player_data[player_id] = json.loads(msg.payload)
        move_flag += 1

def determine_best_target(player_data, player_id):
    pos = player_data["currentPosition"]              #determines current position

    for coin in player_coin_mem[player_id]:   #removes all nearby coins to flush old memory
        x_dist = abs(coin[1] - pos[1])
        y_dist = abs(coin[0] - pos[0])
        if (x_dist <= 2 or y_dist <= 2):
            player_coin_mem[player_id].remove(coin)

    coins = player_data["coin1"] + player_data["coin2"] + player_data["coin3"]

    for coin in coins:                              #readds coins that are still there to update memory
        player_coin_mem[player_id].append(coin)

    coins_left = player_coin_mem[player_id]

    if coins_left:                                         #prioritizes keeping the old target
        player_target = player_targets[player_id]
        if player_target is not None and player_target in coins_left:
            return player_target

        target = min(coins_left, key=lambda coin: math.sqrt((coin[0] - pos[0]) ** 2 + (coin[1] - pos[1]) ** 2))   #determines new target if old target not present
        player_targets[player_id] = target
        return target
    else:                                              #no coins detected, no valid target -> leads to random move
        return None

def determine_next_move(player_data, player_id):
    target = determine_best_target(player_data, player_id)   #determine target
    pos = player_data["currentPosition"]  #determine current and previous position
    prev = previous_pos[player_id]
    obstacles = player_data["enemyPositions"] + player_data["teammatePositions"] + player_data["walls"]  #obstacles given in y,x pairs
    if prev is not None:
        obstacles.append(prev)    #avoid going back to previous position if possible
    x_obstacles = set((obstacle[1], obstacle[0]) for obstacle in obstacles if obstacle[0] == pos[0])
    y_obstacles = set((obstacle[1], obstacle[0]) for obstacle in obstacles if obstacle[1] == pos[1])
    previous_pos[player_id] = pos

    if target is not None:                          #decision logic based on target
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
        
    choices = ["UP", "DOWN", "LEFT", "RIGHT"]          #decision logic has failed or there is no target, player must make a random choice
    if (pos[1] + 1, pos[0]) in x_obstacles or (pos[1] + 1) >= 10: choices.remove("RIGHT")    #remove options that collide with obstacle or go off grid
    if (pos[1] - 1, pos[0]) in x_obstacles or (pos[1] - 1) < 0: choices.remove("LEFT")
    if (pos[1], pos[0] - 1) in y_obstacles or (pos[0] - 1) < 0: choices.remove("UP")
    if (pos[1], pos[0] + 1) in y_obstacles or (pos[0] + 1) >= 10: choices.remove("DOWN")
    if not choices:                    #if no options available, return to previous position
        x_diff = prev[1] - pos[1]
        y_diff = prev[0] - pos[0]
        if x_diff < 0:
            choices.append("LEFT")
        if x_diff > 0:
            choices.append("RIGHT")
        if y_diff < 0:
            choices.append("UP")
        if y_diff > 0:
            choices.append("DOWN")
        if not choices:                          #if all else fails
            choices.append(DEFAULT_CHOICE)
            print("default")
    return random.choice(choices)

if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(paho.CallbackAPIVersion.VERSION1, client_id="Game1", userdata=None, protocol=paho.MQTTv5)
    client.tls_set(tls_version=paho.ssl.PROTOCOL_TLS)
    client.connect(broker_address, broker_port)

    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_publish = on_publish

    lobby_name = input("Please enter lobby name: ")      #creates a lobby based on input
    client.subscribe(f"games/{lobby_name}/lobby")
    for i in range(1, 5):
        client.subscribe(f"games/{lobby_name}/ply{i}/game_state")

    client.subscribe(f"games/{lobby_name}/scores")

    # Initialize player data, targets, coin memory, previous position memory
    player_data = {f"ply{i}": None for i in range(1, 5)}
    player_targets = {f"ply{i}": None for i in range(1, 5)}
    player_coin_mem = {f"ply{i}": [] for i in range(1, 5)}
    previous_pos = {f"ply{i}": None for i in range(1, 5)}

    client.publish("new_game", json.dumps({'lobby_name':lobby_name,            #Adds players to lobby
                                            'team_name':'ATeam',
                                            'player_name' : 'ply1'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'BTeam',
                                            'player_name' : 'ply2'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                        'team_name':'ATeam',
                                        'player_name' : 'ply3'}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                        'team_name':'BTeam',
                                        'player_name' : 'ply4'}))

    # Start the game
    client.publish(f"games/{lobby_name}/start", "START")

    move_flag = 0
    client.loop_start()

    while True:
        try:
            if exit == 1:
                print(exit_reason[2:-1])
                client.publish(f"games/{lobby_name}/start", "STOP")
                print("Scores:", scores)
                break

            while move_flag < 4:      #move flag used to determine feedback has arrived for the moves of each player
                time.sleep(0.1)
            move_flag = 0
            for i in range(1, 5):
                player_id = f"ply{i}"
                move = determine_next_move(player_data[player_id], player_id)     #determines player move
                client.publish(f"games/{lobby_name}/{player_id}/move", move)      #publishes player move
                time.sleep(3)

        except KeyboardInterrupt:                                        #if ctrl+c pressed
            client.publish(f"games/{lobby_name}/start", "STOP")
            break

    client.loop_stop()