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

# spawn EGO
egoState = lgsvl.AgentState()
# Spawn point found in Unity Editor
egoState.transform = sim.map_point_on_lane(lgsvl.Vector(7.36, 0, -50))
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
        'Control'
    ]
    log.warning("LGSVL__AUTOPILOT_0_VEHICLE_MODULES is not set, using default list: {0}".format(modules))

# Ego position is the center of the model.
destination = egoState.position + (120) * forward 
dv.setup_apollo(destination.x, destination.z, modules)


# spawn NPC
npcState = lgsvl.AgentState()
npcState.transform = egoState.transform
npcState.transform.position = egoState.position + 20 * forward # NPC is 3.6m to the left of the EGO
npc = sim.add_agent("SUV", lgsvl.AgentType.NPC, npcState)

npcsState = lgsvl.AgentState()
npcsState.transform = egoState.transform
npcsState.transform.position = egoState.position + 55 * forward  # NPC is 3.6m to the left of the EGO
npcs = sim.add_agent("SUV", lgsvl.AgentType.NPC, npcsState)

# Record result
f = open("../results/result.log", "a")
if int(sys.argv[2]) == 1:
    f.write("Cut out scenario\n")
f.write("beam factors = " + sys.argv[1] + " : ")
# This function will be called if a collision occurs
def on_collision(agent1, agent2, contact):
    global collision
    if not collision:
        f.write("{} collided with {}\n".format(agent1, agent2))
        collision = True
    print("{} collided with {}\n".format(agent1, agent2))

collision = False
ego.on_collision(on_collision)
npc.on_collision(on_collision)
npcs.on_collision(on_collision)


# t0 is the time when the Simulation started
t0 = time.time()

# This will keep track of if the NPC has already changed lanes
npcChangedLanes = False

for sensor in ego.get_sensors():
    if sensor.name == "Lidar":
        print(sensor.rays)
        print(sensor.rotations)
fraction = 1
ego_initial_state = ego.state
minimum_distance = 100
while True:
    npc.follow_closest_lane(follow=True, max_speed=13, isLaneChange=False)
    npcs.follow_closest_lane(follow=True, max_speed=0, isLaneChange=False)
    sim.run(0.25, fraction)
    egoCurrentState = ego.state
    npcCurrentState = npc.state
    npcsCurrentState = npcs.state

    separationDistance = (npcCurrentState.position - npcsCurrentState.position).magnitude()
    separationDistance2 = (egoCurrentState.position - npcsCurrentState.position).magnitude()
    if separationDistance < minimum_distance:
        minimum_distance = separationDistance
    if separationDistance2 < minimum_distance:
        minimum_distance = separationDistance2
    if not npcChangedLanes:
        print(separationDistance)
        if separationDistance <= 25:
            npc.follow_closest_lane(follow=True, max_speed=15, isLaneChange=False)
            npc.change_lane(True)
            npcChangedLanes = True
            sim.run(6, fraction)
    if time.time() - t0 > 20:
        npcs.follow_closest_lane(follow=True, max_speed=7, isLaneChange=False)
        sim.run(30, fraction)

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
