#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MicroPsi runtime module;
maintains a set of users, worlds (up to one per user), and nodenets, and provides an interface to external clients
"""

from micropsi_core._runtime_api_world import *
from micropsi_core._runtime_api_monitors import *

__author__ = 'joscha'
__date__ = '10.05.12'

from configuration import RESOURCE_PATH, SERVER_SETTINGS_PATH, LOGGING

from micropsi_core.nodenet.node import *
from micropsi_core.nodenet.nodenet import *
from micropsi_core.nodenet.nodespace import *

from micropsi_core.nodenet import node_alignment
from micropsi_core import config
from micropsi_core.tools import Bunch
from micropsi_core.tools import NetEntityEncoder
import os
import sys
from micropsi_core import tools
import json
import warnings
from threading import Thread
from datetime import datetime, timedelta
import time
import signal

import logging

from .micropsi_logger import MicropsiLogger

NODENET_DIRECTORY = "nodenets"
WORLD_DIRECTORY = "worlds"

configs = config.ConfigurationManager(SERVER_SETTINGS_PATH)

worlds = {}
nodenets = {}
nodetypes = STANDARD_NODETYPES
native_modules = {}
runner = {
    'nodenet': {'timestep': 1000, 'runner': None},
    'world': {'timestep': 5000, 'runner': None}
}

signal_handler_registry = []

logger = MicropsiLogger({
    'system': LOGGING['level_system'],
    'world': LOGGING['level_world'],
    'nodenet': LOGGING['level_nodenet']
})

def add_signal_handler(handler):
    signal_handler_registry.append(handler)


def signal_handler(signal, frame):
    logging.getLogger('system').info("Shutting down")
    for handler in signal_handler_registry:
        handler(signal, frame)
    sys.exit(0)


def nodenetrunner():
    """Looping thread to simulate node nets continously"""
    while runner['nodenet']['running']:
        if configs['nodenetrunner_timestep'] > 1000:
            step = timedelta(seconds=configs['nodenetrunner_timestep'] / 1000)
        else:
            step = timedelta(milliseconds=configs['nodenetrunner_timestep'])
        start = datetime.now()
        for uid in nodenets:
            if nodenets[uid].is_active:
                try:
                    nodenets[uid].step()
                except:
                    e = sys.exc_info()[1]
                    logging.getLogger("nodenet").error("Exception in NodenetRunner: %s", str(e))
        left = step - (datetime.now() - start)
        if left.total_seconds() > 0:
            time.sleep(left.total_seconds())


def worldrunner():
    """Looping thread to simulate worlds continously"""
    while runner['world']['running']:
        if configs['worldrunner_timestep'] > 1000:
            step = timedelta(seconds=configs['worldrunner_timestep'] / 1000)
        else:
            step = timedelta(milliseconds=configs['worldrunner_timestep'])
        start = datetime.now()
        for uid in worlds:
            if worlds[uid].is_active:
                try:
                    worlds[uid].step()
                except:
                    e = sys.exc_info()[1]
                    logging.getLogger("world").error("Exception in WorldRunner: %s", str(e))
        left = step - (datetime.now() - start)
        if left.total_seconds() > 0:
            time.sleep(left.total_seconds())


def kill_runners(signal, frame):
    runner['world']['running'] = False
    runner['nodenet']['running'] = False
    runner['world']['runner'].join()
    runner['nodenet']['runner'].join()


def _get_world_uid_for_nodenet_uid(nodenet_uid):
    """ Temporary method to get the world uid to a given nodenet uid.
        TODO: I guess this should be handled a bit differently?
    """
    if nodenet_uid in nodenet_data:
        return nodenet_data[nodenet_uid].world
    return None

    '''yes: it should be (if the nodenet is instantiated already):
    nodenet = get_nodenet(nodenet_uid)
    if nodenet:
        return nodenet.world.uid
    return None
    '''

# MicroPsi API

# loggers

def set_logging_levels(system=None, world=None, nodenet=None):
    if system is not None and system in logger.logging_levels:
        logger.set_logging_level('system', system)
    if world is not None and world in logger.logging_levels:
        logger.set_logging_level('world', world)
    if nodenet is not None and nodenet in logger.logging_levels:
        logger.set_logging_level('nodenet', nodenet)
    return True


def get_logger_messages(loggers=[], after=0):
    if not isinstance(loggers, list):
        loggers = [loggers]
    return logger.get_logs(loggers, after)


def get_logging_levels():
    inverse_map = {
        50: 'CRITICAL',
        40: 'ERROR',
        30: 'WARNING',
        20: 'INFO',
        10: 'DEBUG',
        0:'NOTSET'
    }
    levels = {
        'system': inverse_map[logging.getLogger('system').getEffectiveLevel()],
        'world': inverse_map[logging.getLogger('world').getEffectiveLevel()],
        'nodenet': inverse_map[logging.getLogger('nodenet').getEffectiveLevel()],
    }
    return levels

# Minecraft Image
def get_minecraft_image():
    from micropsi_core.world.minecraft.minecraft import Minecraft
    for uid in worlds:
        if isinstance(worlds[uid], Minecraft):
            return worlds[uid].the_image

# Nodenet
def get_available_nodenets(owner=None):
    """Returns a dict of uids: Nodenet of available (running and stored) nodenets.

    Arguments:
        owner (optional): when submitted, the list is filtered by this owner
    """
    if owner:
        return dict(
            (uid, nodenet_data[uid]) for uid in nodenet_data if nodenet_data[uid].owner == owner)
    else:
        return nodenet_data

def get_nodenet(nodenet_uid):
    """Returns the nodenet with the given uid, and loads into memory if necessary.
    Returns None if nodenet does not exist"""
    if nodenet_uid not in nodenets:
        if nodenet_uid in get_available_nodenets():
            load_nodenet(nodenet_uid)
        else:
            return None
    return nodenets[nodenet_uid]


def get_nodenet_or_none(nodenet_uid):
    """Returns the nodenet with the given uid, and loads into memory if necessary.
    Returns None if nodenet does not exist"""
    if nodenet_uid not in nodenets:
        return None
    return nodenets[nodenet_uid]

def load_nodenet(nodenet_uid):
    """ Load the nodenet with the given uid into memeory
        TODO: how do we know in which world we want to load the nodenet?
        I've added the world uid to the nodenet serialized data for the moment

        Arguments:
            nodenet_uid
        Returns:
             True, nodenet_uid on success
             False, errormessage on failure

    """
    if nodenet_uid in nodenet_data:
        world = worldadapter = None
        if nodenet_uid not in nodenets:
            data = nodenet_data[nodenet_uid]

            if data.get('world'):
                if data.world in worlds:
                    world = worlds.get(data.world)
                    worldadapter = data.get('worldadapter')
            nodenet = Nodenet()
            nodenets[nodenet_uid] = nodenet
            nodenet.init(
                os.path.join(RESOURCE_PATH, NODENET_DIRECTORY,  nodenet_uid + '.json'),
                name=data.name, worldadapter=worldadapter,
                world=world, owner=data.owner, uid=data.uid,
                nodetypes=nodetypes, native_modules=native_modules)
        else:
            world = nodenets[nodenet_uid].world or None
            worldadapter = nodenets[nodenet_uid].worldadapter
        if world:
            world.register_nodenet(worldadapter, nodenets[nodenet_uid])
        return True, nodenet_uid
    return False, "Nodenet "+nodenet_uid+" not found in "+RESOURCE_PATH

def get_nodenet_data(nodenet_uid, **coordinates):
    """ returns the current state of the nodenet """
    nodenet = get_nodenet(nodenet_uid)
    with nodenet.netlock:
        data = nodenet.state.copy()
    data.update(get_nodenet_area(nodenet_uid, **coordinates))
    data.update({
        'nodetypes': nodetypes,
        'native_modules': native_modules
    })
    return data


def unload_nodenet(nodenet_uid):
    """ Unload the nodenet.
        Deletes the instance of this nodenet without deleting it from the storage

        Arguments:
            nodenet_uid
    """
    if not nodenet_uid in nodenets:
        return False
    nodenets[nodenet_uid].unload()
    del nodenets[nodenet_uid]
    return True

def get_nodenet_area(nodenet_uid, nodespace="Root", x1=0, x2=-1, y1=0, y2=-1):
    """ returns part of the nodespace for representation in the UI
    Either you specify an area to be retrieved, or the retrieval is limited to 500 nodes currently
    """
    if nodespace not in nodenets[nodenet_uid].nodespaces:
        nodespace = "Root"
    with nodenets[nodenet_uid].netlock:
        if x2 < 0 or y2 < 0:
            data = nodenets[nodenet_uid].get_nodespace(nodespace, 500)
        else:
            data = nodenets[nodenet_uid].get_nodespace_area(nodespace, x1, x2, y1, y2)
        data['nodespace'] = nodespace
        return data


def new_nodenet(nodenet_name, worldadapter, template=None, owner="", world_uid=None, uid=None):
    """Creates a new node net manager and registers it.

    Arguments:
        worldadapter: the type of the world adapter supported by this nodenet. Also used to determine the set of
            gate types supported for directional activation spreading of this nodenet, and the initial node types
        owner (optional): the creator of this nodenet
        world_uid (optional): if submitted, attempts to bind the nodenet to this world
        uid (optional): if submitted, this is used as the UID for the nodenet (normally, this is generated)

    Returns
        nodenet_uid if successful,
        None if failure
    """
    if template is not None and template in nodenet_data:
        if template in nodenets:
            data = nodenets[template].state.copy()
        else:
            data = nodenet_data[template].copy()
    else:
        data = dict(
            nodes=dict(),
            links=dict(),
            step=0,
            version=1
        )
    if not uid:
        uid = tools.generate_uid()
    data.update(dict(
        uid=uid,
        name=nodenet_name,
        worldadapter=worldadapter,
        owner=owner,
        world=world_uid
    ))
    filename = os.path.join(RESOURCE_PATH, NODENET_DIRECTORY, data['uid'] + ".json")
    nodenet_data[data['uid']] = Bunch(**data)
    with open(filename, 'w+') as fp:
        fp.write(json.dumps(data, cls=NetEntityEncoder, sort_keys=True, indent=4))
    fp.close()
    #load_nodenet(data['uid'])
    return True, data['uid']


def clear_nodenet(nodenet_uid):
    """Deletes all contents of a nodenet"""
    nodenet = get_nodenet(nodenet_uid)
    nodenet.clear()
    return True


def delete_nodenet(nodenet_uid):
    """Unloads the given nodenet from memory and deletes it from the storage.

    Simple unloading is maintained automatically when a nodenet is suspended and another one is accessed.
    """
    unload_nodenet(nodenet_uid)
    filename = os.path.join(RESOURCE_PATH, NODENET_DIRECTORY, nodenet_uid + '.json')
    os.remove(filename)
    del nodenet_data[nodenet_uid]
    return True


def set_nodenet_properties(nodenet_uid, nodenet_name=None, worldadapter=None, world_uid=None, owner=None):
    """Sets the supplied parameters (and only those) for the nodenet with the given uid."""
    nodenet = nodenets[nodenet_uid]
    if nodenet.world and nodenet.world.uid != world_uid:
        nodenet.world.unregister_nodenet(nodenet_uid)
        nodenet.world = None
    if worldadapter is None:
        worldadapter = nodenet.worldadapter
    if world_uid is not None and worldadapter is not None:
        assert worldadapter in worlds[world_uid].supported_worldadapters
        nodenet.world = worlds[world_uid]
        nodenet.worldadapter = worldadapter
        worlds[world_uid].register_nodenet(worldadapter, nodenet)
    if nodenet_name:
        nodenet.name = nodenet_name
    if owner:
        nodenet.owner = owner
    nodenet_data[nodenet_uid] = Bunch(**nodenet.state)
    return True


def start_nodenetrunner(nodenet_uid):
    """Starts a thread that regularly advances the given nodenet by one step."""
    nodenets[nodenet_uid].is_active = True
    return True


def set_nodenetrunner_timestep(timestep):
    """Sets the speed of the nodenet simulation in ms.

    Argument:
        timestep: sets the simulation speed.
    """
    configs['nodenetrunner_timestep'] = timestep
    runner['nodenet']['timestep'] = timestep
    return True


def get_nodenetrunner_timestep():
    """Returns the speed that has been configured for the nodenet runner (in ms)."""
    return configs['nodenetrunner_timestep']


def get_is_nodenet_running(nodenet_uid):
    """Returns True if a nodenet runner is active for the given nodenet, False otherwise."""
    return nodenets[nodenet_uid].is_active


def stop_nodenetrunner(nodenet_uid):
    """Stops the thread for the given nodenet."""
    nodenets[nodenet_uid].is_active = False
    return True


def step_nodenet(nodenet_uid, nodespace=None):
    """Advances the given nodenet by one simulation step.

    Arguments:
        nodenet_uid: The uid of the nodenet
        nodespace (optional): when supplied, returns the contents of the nodespace after the simulation step
    """
    # if nodespace is not None:
    #     nodenets[nodenet_uid].step_nodespace(nodespace)
    # else:
    nodenets[nodenet_uid].step()
    return nodenets[nodenet_uid].current_step


def revert_nodenet(nodenet_uid):
    """Returns the nodenet to the last saved state."""
    unload_nodenet(nodenet_uid)
    load_nodenet(nodenet_uid)
    return True


def save_nodenet(nodenet_uid):
    """Stores the nodenet on the server (but keeps it open)."""
    nodenet = nodenets[nodenet_uid]
    with open(os.path.join(RESOURCE_PATH, NODENET_DIRECTORY, nodenet_uid + '.json'), 'w+') as fp:
        fp.write(json.dumps(nodenet.state, cls=NetEntityEncoder, sort_keys=True, indent=4))
    fp.close()
    return True


def export_nodenet(nodenet_uid):
    """Exports the nodenet state to the user, so it can be viewed and exchanged.

    Returns a string that contains the nodenet state in JSON format.
    """
    return json.dumps(nodenets[nodenet_uid].state, cls=NetEntityEncoder, sort_keys=True, indent=4)


def import_nodenet(string, owner=None):
    """Imports the nodenet state, instantiates the nodenet.

    Arguments:
        nodenet_uid: the uid of the nodenet (may overwrite existing nodenet)
        string: a string that contains the nodenet state in JSON format.
    """
    global nodenet_data
    import_data = json.loads(string)
    if 'uid' not in import_data:
        import_data['uid'] = tools.generate_uid()
    if 'owner':
        import_data['owner'] = owner
    # assert import_data['world'] in worlds
    filename = os.path.join(RESOURCE_PATH, NODENET_DIRECTORY, import_data['uid'] + '.json')
    with open(filename, 'w+') as fp:
        fp.write(json.dumps(import_data,cls=NetEntityEncoder,))
    fp.close()
    nodenet_data[import_data['uid']] = parse_definition(import_data, filename)
    return True


def merge_nodenet(nodenet_uid, string):
    """Merges the nodenet data with an existing nodenet, instantiates the nodenet.

    Arguments:
        nodenet_uid: the uid of the existing nodenet (may overwrite existing nodenet)
        string: a string that contains the nodenet data that is to be merged in JSON format.
    """
    nodenet = nodenets[nodenet_uid]
    data = json.loads(string)
    nodenet.merge_data(data)
    save_nodenet(nodenet_uid)
    unload_nodenet(nodenet_uid)
    load_nodenet(nodenet_uid)
    return True


def copy_nodes(node_uids, source_nodenet_uid, target_nodenet_uid, target_nodespace_uid="Root",
               copy_associated_links=True):
    """Copies a set of netentities, either between nodenets or within a nodenet. If a target nodespace
    is supplied, all nodes will be inserted below that target nodespace, otherwise below "Root".
    If parent nodespaces are included in the set of node_uids, the contained nodes will remain in
    these parent nodespaces.
    Only explicitly listed nodes and nodespaces will be copied.
    UIDs will be kept if possible, but renamed in case of conflicts.

    Arguments:
        node_uids: a list of uids of nodes and nodespaces
        source_nodenet_uid
        target_nodenet_uid
        target_nodespace_uid: the uid of the nodespace into which the nodes will be copied
        copy_associated_links: if True, links to not-copied nodes will be copied, too (of course, this works
            only within the same nodenet)
    """
    source_nodenet = nodenets[source_nodenet_uid]
    target_nodenet = nodenets[target_nodenet_uid]
    nodes = {}
    nodespaces = {}
    for node_uid in node_uids:
        if node_uid in source_nodenet.nodes:
            nodes[node_uid] = source_nodenet.nodes[node_uid]
        elif node_uid in source_nodenet.nodespaces:
            nodespaces[node_uid] = source_nodenet.nodespaces[node_uid]
    target_nodenet.copy_nodes(nodes, nodespaces, target_nodespace_uid, copy_associated_links)
    return True


# Node operations

def get_nodespace_list(nodenet_uid):
    """ returns a list of nodespaces in the given nodenet. information includes:
     - nodespace name,
     - nodespace parent
     - a list of nodes (uid, name, and type) residing in that nodespace
    """
    nodenet = nodenets[nodenet_uid]
    data = {}
    for uid, nodespace in nodenet.nodespaces.items():
        data[uid] = {
            'name': nodespace.name,
            'parent': nodespace.parent_nodespace,
            'nodes': {},
            'gatefunctions': {}
        }
        for nid in nodespace.netentities.get('nodes', []):
            data[uid]['nodes'][nid] = {
                'name': nodenet.nodes[nid].name,
                'type': nodenet.nodes[nid].type,
                'gates': nodenet.get_nodetype(nodenet.nodes[nid].type).gatetypes,
                'slots': nodenet.get_nodetype(nodenet.nodes[nid].type).slottypes
            }
        data[uid]['gatefunctions'] = nodespace.gatefunctions
    return data


def get_nodespace(nodenet_uid, nodespace, step, **coordinates):
    """Returns the current state of the nodespace for UI purposes, if current step is newer than supplied one."""
    data = {}
    if step < nodenets[nodenet_uid].current_step:
        data = get_nodenet_area(nodenet_uid, nodespace, **coordinates)
        data.update({'current_step': nodenets[nodenet_uid].current_step, 'is_active': nodenets[nodenet_uid].is_active})
    return data


def get_node(nodenet_uid, node_uid):
    """Returns a dictionary with all node parameters, if node exists, or None if it does not. The dict is
    structured as follows:
        {
            uid: unique identifier,
            name (optional): display name,
            type: node type,
            parent: parent nodespace,
            x (optional): x position,
            y (optional): y position,
            activation: activation value,
            symbol (optional): a short string for compact display purposes,
            slots (optional): a list of lists [slot_type, {activation: activation_value,
                                                           links (optional): [link_uids]} (optional)]
            gates (optional): a list of lists [gate_type, {activation: activation_value,
                                                           function: gate_function (optional),
                                                           params: {gate_parameters} (optional),
                                                           links (optional): [link_uids]} (optional)]
            parameters (optional): a dict of arbitrary parameters that can make nodes stateful
        }
     """
    return nodenets[nodenet_uid].nodes[node_uid]


def add_node(nodenet_uid, type, pos, nodespace="Root", state=None, uid=None, name="", parameters=None):
    """Creates a new node. (Including nodespace, native module.)

    Arguments:
        nodenet_uid: uid of the nodespace manager
        type: type of the node
        position: position of the node in the current nodespace
        nodespace: uid of the nodespace
        uid (optional): if not supplied, a uid will be generated
        name (optional): if not supplied, the uid will be used instead of a display name
        parameters (optional): a dict of arbitrary parameters that can make nodes stateful

    Returns:
        node_uid if successful,
        None if failure.
    """
    nodenet = get_nodenet(nodenet_uid)
    if type == "Nodespace":
        nodespace = Nodespace_class().new(nodenet, nodespace, pos, name=name, uid=uid)
        uid = nodespace.uid
    else:
        node = Node.new(nodenet, nodespace, pos, name=name, type=type, uid=uid, parameters=parameters)
        uid = node.uid
        nodenet.update_node_positions()
    return True, uid


def set_node_position(nodenet_uid, node_uid, pos):
    """Positions the specified node at the given coordinates."""
    nodenet = nodenets[nodenet_uid]
    if node_uid in nodenet.nodes:
        nodenet.nodes[node_uid].position = pos
    elif node_uid in nodenet.nodespaces:
        nodenet.nodespaces[node_uid].position = pos
    nodenet.update_node_positions()
    return True


def set_node_name(nodenet_uid, node_uid, name):
    """Sets the display name of the node"""
    nodenet = nodenets[nodenet_uid]
    if node_uid in nodenet.nodes:
        nodenet.nodes[node_uid].name = name
    elif node_uid in nodenet.nodespaces:
        nodenet.nodespaces[node_uid].name = name
    return True


def set_node_state(nodenet_uid, node_uid, state):
    """ Sets the state of the given node to the given state,
        provided, the nodetype allows the given state """
    node = nodenets[nodenet_uid].nodes[node_uid]
    if state and state in node.nodetype.states:
        node.state = state
        return True
    return False


def set_node_activation(nodenet_uid, node_uid, activation):
    nodenets[nodenet_uid].nodes[node_uid].activation = activation
    return True


def delete_node(nodenet_uid, node_uid):
    """Removes the node"""
    nodenets[nodenet_uid].delete_node(node_uid)
    return True


def get_available_node_types(nodenet_uid=None):
    """Returns a list of available node types. (Including native modules.)"""
    all_nodetypes = native_modules.copy()
    all_nodetypes.update(nodetypes)
    return all_nodetypes


def get_available_native_module_types(nodenet_uid):
    """Returns a list of native modules.
    If an nodenet uid is supplied, filter for node types defined within this nodenet."""
    return native_modules


def get_nodefunction(nodenet_uid, node_type):
    """Returns the current node function for this node type"""
    nodefunc_def = nodenets[nodenet_uid].get_nodetype(node_type).nodefunction_definition
    nodefunc_name = nodenets[nodenet_uid].get_nodetype(node_type).nodefunction_name
    if not nodefunc_def:
        return "nodefunctions.%s" % nodefunc_name
    return nodefunc_def


def set_nodefunction(nodenet_uid, node_type, nodefunction=None):
    """Sets a new node function for this node type. This amounts to a program that is executed every time the
    node becomes active. Parameters of the function are the node itself (and thus, its slots, gates and
    parent nodespace), the nodenet, and the parameter dict of this node).
    Setting the node_function to None will return it to its default state (passing the slot activations to
    all gate functions).
    """
    nodenets[nodenet_uid].get_nodetype(node_type).nodefunction_definition = nodefunction
    return True


def set_node_parameters(nodenet_uid, node_uid, parameters):
    """Sets a dict of arbitrary values to make the node stateful."""
    nodenets[nodenet_uid].nodes[node_uid].set_parameters(parameters)
    return True


def add_node_type(nodenet_uid, node_type, slots=None, gates=None, node_function=None, parameters=None):
    """Adds or modifies a native module.

    Arguments:
        nodenet_uid: the nodenet into which the native module will be saved
        node_type: the identifier of the native module. If it already exists for another user, the new definition
            will hide the old one from view.
        node_function (optional): the program code of the native module. The native module is defined as a
            python function that takes the current node, the nodenet manager and the node parameters as arguments.
            The default node function takes the slot activations and calls all gatefunctions with
            it as an argument.
        slots (optional): the list of slot types for this node type
        gates (optional): the list of gate types for this node type
        parameters (optional): a dict of arbitrary parameters that can be used by the nodefunction to store states
    """
    nodenet = nodenets[nodenet_uid]
    nodenet.native_modules[node_type] = Nodetype(node_type, nodenet, slots, gates, [], parameters,
        nodefunction_definition=node_function)
    native_modules[node_type] = nodenet.native_modules[node_type].state.copy()
    return True


def delete_node_type(nodenet_uid, node_type):
    """Remove the node type from the current nodenet definition, if it is part of it."""
    # try:
    #     del nodenets[nodenet_uid].state['nodetypes'][node_type]
    #     return True
    # except KeyError:
    return False


def get_slot_types(nodenet_uid, node_type):
    """Returns the list of slot types for the given node type."""
    return nodenets[nodenet_uid].get_nodetype(node_type).slottypes


def get_gate_types(nodenet_uid, node_type):
    """Returns the list of gate types for the given node type."""
    return nodenets[nodenet_uid].get_nodetype(node_type).gatetypes


def get_gate_function(nodenet_uid, nodespace, node_type, gate_type):
    """Returns a string with the gate function of the given node and gate within the current nodespace.
    Gate functions are defined per nodespace, and handed the parameters dictionary. They must return an activation.
    """
    return nodenets[nodenet_uid].state['nodespaces'][nodespace]['gatefunctions'].get(node_type, {}).get(
        gate_type)


def set_gate_function(nodenet_uid, nodespace, node_type, gate_type, gate_function=None, parameters=None):
    """Sets the gate function of the given node and gate within the current nodespace.
    Gate functions are defined per nodespace, and handed the parameters dictionary. They must return an activation.
    The default function is a threshold with parameter t=0.
    None reverts the custom gate function of the given node and gate within the current nodespace to the default.
    Parameters is a list of keys for values of the gate function.
    """
    nodenets[nodenet_uid].nodespaces[nodespace].set_gate_function(node_type, gate_type, gate_function,
        parameters)
    return True


def set_gate_parameters(nodenet_uid, node_uid, gate_type, parameters=None):
    """Sets the gate parameters of the given gate of the given node to the supplied dictionary."""
    nodenets[nodenet_uid].nodes[node_uid].set_gate_parameters(gate_type, parameters)
    return True


def get_available_datasources(nodenet_uid):
    """Returns a list of available datasource types for the given nodenet."""
    return worlds[_get_world_uid_for_nodenet_uid(nodenet_uid)].get_available_datasources(nodenet_uid)


def get_available_datatargets(nodenet_uid):
    """Returns a list of available datatarget types for the given nodenet."""
    return worlds[_get_world_uid_for_nodenet_uid(nodenet_uid)].get_available_datatargets(nodenet_uid)


def bind_datasource_to_sensor(nodenet_uid, sensor_uid, datasource):
    """Associates the datasource type to the sensor node with the given uid."""
    node = nodenets[nodenet_uid].nodes[sensor_uid]
    if node.type == "Sensor":
        node.parameters.update({'datasource': datasource})
        return True
    return False


def bind_datatarget_to_actor(nodenet_uid, actor_uid, datatarget):
    """Associates the datatarget type to the actor node with the given uid."""
    node = nodenets[nodenet_uid].nodes[actor_uid]
    if node.type == "Actor":
        node.parameters.update({'datatarget': datatarget})
        return True
    return False

def get_link(nodenet_uid, source_node_uid, gate_type, target_node_uid, slot_type ):
    nodenet = nodenets[nodenet_uid]
    source_node = nodenet.nodes[source_node_uid]
    target_node = nodenet.nodes[target_node_uid]
    return source_node.get_gate_link(gate_type,target_node,slot_type).get_data()

def add_link(nodenet_uid, source_node_uid, gate_type, target_node_uid, slot_type, weight=1, certainty=1, uid=None):
    """Creates a new link.

    Arguments.
        source_node_uid: uid of the origin node
        gate_type: type of the origin gate (usually defines the link type)
        target_node_uid: uid of the target node
        slot_type: type of the target slot
        weight: the weight of the link (a float)
        certainty (optional): a probabilistic parameter for the link
        uid (option): if none is supplied, a uid will be generated

    Returns:
        link_uid if successful,
        None if failure
    """
    nodenet = nodenets[nodenet_uid]
    nodenet.create_link(source_node_uid, gate_type, target_node_uid, slot_type, weight, certainty )
    return True


def set_link_weight(nodenet_uid, link_uid, weight, certainty=1):
    """Set weight of the given link."""
    nodenet = nodenets[nodenet_uid]
    return nodenet.set_link_weight(link_uid, weight, certainty)


def delete_link(nodenet_uid, link_uid):
    """Delete the given link."""
    nodenet = nodenets[nodenet_uid]
    return nodenet.delete_link(link_uid)


def align_nodes(nodenet_uid, nodespace):
    """Perform auto-alignment of nodes in the current nodespace"""
    result = node_alignment.align(nodenets[nodenet_uid], nodespace)
    if result:
        nodenets[nodenet_uid].update_node_positions()
    return result


def user_prompt_response(nodenet_uid, node_uid, values, resume_nodenet):
    nodenets[nodenet_uid].nodes[node_uid].parameters.update(values)
    nodenets[nodenet_uid].is_active = resume_nodenet


# --- end of API

def crawl_definition_files(path, type="definition"):
    """Traverse the directories below the given path for JSON definitions of nodenets and worlds,
    and return a dictionary with the signatures of these nodenets or worlds.
    """

    result = {}
    tools.mkdir(path)

    for user_directory_name, user_directory_names, file_names in os.walk(path):
        for definition_file_name in file_names:
            try:
                filename = os.path.join(user_directory_name, definition_file_name)
                with open(filename) as file:
                    data = parse_definition(json.load(file), filename)
                    result[data.uid] = data
            except ValueError:
                warnings.warn("Invalid %s data in file '%s'" % (type, definition_file_name))
            except IOError:
                warnings.warn("Could not open %s data file '%s'" % (type, definition_file_name))
    return result


def parse_definition(json, filename=None):
    if "uid" in json:
        result = dict(
            uid=json["uid"],
            name=json.get("name", json["uid"]),
            filename=filename or json.get("filename"),
            owner=json.get("owner")
        )
        if "worldadapter" in json:
            result['worldadapter'] = json["worldadapter"]
            result['world'] = json["world"]
        if "world_type" in json:
            result['world_type'] = json['world_type']
        return Bunch(**result)


# Set up the MicroPsi runtime
def load_definitions():
    global nodenet_data, world_data
    nodenet_data = crawl_definition_files(path=os.path.join(RESOURCE_PATH, NODENET_DIRECTORY), type="nodenet")
    world_data = crawl_definition_files(path=os.path.join(RESOURCE_PATH, WORLD_DIRECTORY), type="world")
    if not world_data:
        # create a default world for convenience.
        uid = tools.generate_uid()
        filename = os.path.join(RESOURCE_PATH, WORLD_DIRECTORY, uid + '.json')
        world_data[uid] = Bunch(uid=uid, name="default", version=1, filename=filename)
        with open(filename, 'w+') as fp:
            fp.write(json.dumps(world_data[uid], cls=NetEntityEncoder, sort_keys=True, indent=4))
        fp.close()
    return nodenet_data, world_data


# set up all worlds referred to in the world_data:
def init_worlds(world_data):
    global worlds
    for uid in world_data:
        if "world_type" in world_data[uid]:
            try:
                worlds[uid] = get_world_class_from_name(world_data[uid].world_type)(**world_data[uid])
            except TypeError:
                worlds[uid] = world.World(**world_data[uid])
            except AttributeError as err:
                warnings.warn("Unknown world_type: %s (%s)" % (world_data[uid].world_type, str(err)))
        else:
            worlds[uid] = world.World(**world_data[uid])
    return worlds


def load_user_files(do_reload=False):
    # see if we have additional nodetypes defined by the user.
    global native_modules
    old_native_modules = native_modules.copy()
    native_modules = {}
    custom_nodetype_file = os.path.join(RESOURCE_PATH, 'nodetypes.json')
    if os.path.isfile(custom_nodetype_file):
        try:
            with open(custom_nodetype_file) as fp:
                native_modules = json.load(fp)
        except ValueError:
            warnings.warn("Nodetype data in %s not well-formed." % custom_nodetype_file)

    if do_reload and old_native_modules != {}:
        for key in old_native_modules:
            if key not in native_modules:
                native_modules[key] = old_native_modules[key]
                warnings.warn("Deleting native modules during runtime is unsafe. Restoring native module %s" % key)

    # respect user defined nodefunctions:
    if os.path.isfile(os.path.join(RESOURCE_PATH, 'nodefunctions.py')):
        import sys
        sys.path.append(RESOURCE_PATH)

    return native_modules


def reload_native_modules(nodenet_uid=None):
    load_user_files(True)
    if nodenet_uid:
        for key in native_modules:
            if key not in nodenets[nodenet_uid].native_modules:
                nodenets[nodenet_uid].native_modules[key] = Nodetype(nodenet=nodenets[nodenet_uid], **native_modules[key])
            nodenets[nodenet_uid].native_modules[key].reload_nodefunction()
    return True


load_definitions()
init_worlds(world_data)
load_user_files()

# initialize runners
# Initialize the threads for the continuous simulation of nodenets and worlds
if 'worldrunner_timestep' not in configs:
    configs['worldrunner_timestep'] = 5000
    configs['nodenetrunner_timestep'] = 1000
    configs.save_configs()
runner['world']['running'] = True
runner['world']['runner'] = Thread(target=worldrunner)
runner['world']['runner'].daemon = True
runner['nodenet']['running'] = True
runner['nodenet']['runner'] = Thread(target=nodenetrunner)
runner['nodenet']['runner'].daemon = True
runner['world']['runner'].start()
runner['nodenet']['runner'].start()

add_signal_handler(kill_runners)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

from micropsi_core.strongcore_micropsi import *