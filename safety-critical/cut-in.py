#!/usr/bin/env python3
#
# Copyright (c) 2019 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

# LGSVL__SIMULATOR_HOST and LGSVL__AUTOPILOT_0_HOST are environment variables
# They can be set for the terminal instance with `export LGSVL__SIMULATOR_HOST=###`
# which will use the set value for all future commands in that terminal.
# To set the variable for only a particular execution, run the script in this way
# `LGSVL__SIMULATOR_HOST=### LGSVL__AUTOPILOT_0_HOST=### python3 cut-in.py`

# LGSVL__SIMULATOR_HOST is the IP of the computer running the simulator
# LGSVL__AUTOPILOT_0_HOST is the IP of the computer running the bridge (from the perspective of the Simulator)
# If the simulator and bridge are running on the same computer, then the default values will work.
# Otherwise the variables must be set for in order to connect to the simulator and the bridge to receive data.
# LGSVL__SIMULATOR_PORT and LGSVL__AUTOPILOT_0_HOST need to be set if non-default ports will be used

import os
import paramiko
import lgsvl
import logging

from environs import Env

import time
import sys

FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
log = logging.getLogger(__name__)

server = "100.89.7.162"
username = "yushun"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(server, username=username)

cmd_to_execute = "sed -i -e 's/.*--downsample_beams_factor.*/--downsample_beams_factor=" + str(sys.argv[1]) + "/g' /home/yushun/Desktop/apollo/modules/perception/production/conf/perception/perception_common.flag"
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)
ssh.close()

env = Env()

SIMULATOR_HOST = env.str("LGSVL__SIMULATOR_HOST", "127.0.0.1")
SIMULATOR_PORT = env.int("LGSVL__SIMULATOR_PORT", 8181)
BRIDGE_HOST = env.str("LGSVL__AUTOPILOT_0_HOST", "100.89.7.162")
BRIDGE_PORT = env.int("LGSVL__AUTOPILOT_0_PORT", 9090)
scene_name = env.str("LGSVL__MAP", lgsvl.wise.DefaultAssets.map_straight2lanesame)
sim = lgsvl.Simulator(SIMULATOR_HOST, SIMULATOR_PORT)
if sim.current_scene == scene_name:
    sim.reset()
else:
    sim.load(scene_name)
sim.add_random_agents(lgsvl.AgentType.NPC)
# spawn EGO
egoState = lgsvl.AgentState()
# Spawn point found in Unity Editor
egoState.transform = sim.map_point_on_lane(lgsvl.Vector(7.36, 0, -50))
# For SanFrancisco
ego = sim.add_agent(os.environ.get("LGSVL__VEHICLE_0", lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo5_full_analysis_test), lgsvl.AgentType.EGO, egoState)

ego.connect_bridge(BRIDGE_HOST, BRIDGE_PORT)

right = lgsvl.utils.transform_to_right(egoState.transform) # Unit vector in the right direction of the EGO
forward = lgsvl.utils.transform_to_forward(egoState.transform) # Unit vector in the forward direction of the EGO

dv = lgsvl.dreamview.Connection(sim, ego, BRIDGE_HOST)
dv.set_hd_map(env.str("LGSVL__AUTOPILOT_HD_MAP", 'Straight2LaneSame'))
dv.set_vehicle(env.str("LGSVL__AUTOPILOT_0_VEHICLE_CONFIG", 'Lincoln2017MKZ'))
try:
    modules = env.list("LGSVL__AUTOPILOT_0_VEHICLE_MODULES", subcast=str)
    if len(modules) == 0:
        log.warning("LGSVL__AUTOPILOT_0_VEHICLE_MODULES is empty, using default list: {0}".format(modules))
        modules = [
            'Recorder',
            'Localization',
            'Perception',
            'Transform',
            'Routing',
            'Prediction',
            'Planning',
            'Traffic Light',
            'Control'
        ]
except Exception:
    modules = [
        'Localization',
        'Perception',
        'Transform',
        'Routing',
        'Prediction',
        'Planning',
        #'Camera',
        #'Traffic Light',
        'Control'
    ]
    log.warning("LGSVL__AUTOPILOT_0_VEHICLE_MODULES is not set, using default list: {0}".format(modules))

# Ego position is the center of the model.
# Destination is half EGO length + NPC length + EGO-NPC bumper distance + half parking zone length ahead of EGO
destination = egoState.position + (120) * forward 
dv.setup_apollo(destination.x, destination.z, modules)


# spawn NPC
npcState = lgsvl.AgentState()
npcState.transform.position = egoState.position + 50 * forward - 3.6 * right # NPC is 3.6m to the left of the EGO
npc = sim.add_agent("Jeep", lgsvl.AgentType.NPC, npcState)
'''
npc1State = lgsvl.AgentState()
npc1State.transform.position = egoState.position + 70 * forward - 3.6 * right # NPC is 3.6m to the left of the EGO
npc1 = sim.add_agent("Sedan", lgsvl.AgentType.NPC, npc1State)

npc2State = lgsvl.AgentState()
npc2State.transform.position = egoState.position + 70 * forward # NPC is 3.6m to the left of the EGO
npc2 = sim.add_agent("SUV", lgsvl.AgentType.NPC, npc2State)

npc3State = lgsvl.AgentState()
npc3State.transform.position = egoState.position + 10 * forward - 3.6 * right   # NPC is 3.6m to the left of the EGO
npc3 = sim.add_agent("SchoolBus", lgsvl.AgentType.NPC, npc3State)
'''
# Record result
f = open("../results/result.log", "a")
if int(sys.argv[2]) == 1:
    f.write("Cut in scenario\n")

f.write("beam factors = " + sys.argv[1] + " : ")
# This function will be called if a collision occurs
def on_collision(agent1, agent2, contact):
    global collision
    if not collision:
        f.write("{} collided with {}\n".format(agent1, agent2))
        collision = True
    print("{} collided with {}\n".format(agent1, agent2))
    #raise Exception("{} collided with {}\n".format(agent1, agent2))

collision = False
ego.on_collision(on_collision)
npc.on_collision(on_collision)



#sim.run(30)


# NPC will follow the HD map at a max speed of 15 m/s (33 mph) and will not change lanes automatically
# The speed limit of the road is 20m/s so the EGO should drive faster than the NPC

# t0 is the time when the Simulation started
t0 = time.time()

# This will keep track of if the NPC has already changed lanes
npcChangedLanes = False

for sensor in ego.get_sensors():
    #print(sensor.name)
    if sensor.name == "Lidar":
        print(sensor.rays)
        print(sensor.rotations)
fraction = 1
#print(ego.state)
ego_initial_state = ego.state
minimum_distance = 100
while True:
    sim.run(0.25, fraction)
    # If the NPC has not already changed lanes then the distance between the NPC and EGO is calculated
    '''
    npc.follow_closest_lane(follow=True, max_speed=7, isLaneChange=False)
    npc1.follow_closest_lane(follow=True, max_speed=7, isLaneChange=False)
    npc2.follow_closest_lane(follow=True, max_speed=7, isLaneChange=False)
    npc3.follow_closest_lane(follow=True, max_speed=7, isLaneChange=False)
    '''
    #print("Ego: ", ego.state, "npc: ", npc.state, "\n")
    egoCurrentState = ego.state
    npcCurrentState = npc.state
    separationDistance = (egoCurrentState.position - npcCurrentState.position).magnitude()
    if separationDistance < minimum_distance:
        minimum_distance = separationDistance
    if not npcChangedLanes:
        # If the EGO and NPC are within 10m, then NPC will change lanes to the right (in front of the EGO)
        if separationDistance <= 13:
            npc.follow_closest_lane(follow=True, max_speed=8, isLaneChange=False)
            npc.change_lane(False)
            npcChangedLanes = True
            sim.run(4 , fraction)
            npc.follow_closest_lane(follow=True, max_speed=1, isLaneChange=False)
            sim.run(2, fraction)
            npc.follow_closest_lane(follow=True, max_speed=10, isLaneChange=False)

    # Simulation will be limited to running for 30 seconds total
    if time.time() - t0 > 45*(1/fraction):
        break

dv.disable_apollo()
stopZoneBeginning = sim.map_point_on_lane(ego_initial_state.position + 105 * forward)
stopZoneEnd = sim.map_point_on_lane(stopZoneBeginning.position + 10 * forward)
finalEgoState = ego.state
print(finalEgoState)

csvf = open("../results/result.csv", "a")
for sensor in ego.get_sensors():
    if sensor.name == "Lidar":
        if int(sys.argv[2]) == 1:
            csvf.write(","+ str(sensor.rays)+","+str(sensor.rotations))
csvf_min_d = open("../results/result_min_d.csv", "a")
for sensor in ego.get_sensors():
    if sensor.name == "Lidar":
        if int(sys.argv[2]) == 1:
            csvf_min_d.write(","+ str(sensor.rays)+","+str(sensor.rotations))
if collision:
    csvf.write(",1")
    csvf_min_d.write(",0")
else:
    csvf.write(",0")
    csvf_min_d.write(","+str(minimum_distance))

try:
    if not lgsvl.evaluator.right_lane_check(sim, finalEgoState.transform):
        f.write("Ego change lanes\n")
        raise lgsvl.evaluator.TestException("Ego change lanes\n")
    elif not lgsvl.evaluator.in_parking_zone(
        stopZoneBeginning.position,
        stopZoneEnd.position,
        finalEgoState.transform
    ):
        f.write("Ego did not stop in stopping zone\n")
        raise lgsvl.evaluator.TestException("Ego did not stop in stopping zone\n")
    elif finalEgoState.speed > 0.2:
        f.write("Ego did not stop\n")
        raise lgsvl.evaluator.TestException("Ego did not stop\n")
    else:
        if not collision:
            f.write("PASSED\n")
            print("PASSED\n")
except ValueError as e:
    f.write("FAILED: {}\n".format(e))
    exit("FAILED: {}\n".format(e))
f.close()
