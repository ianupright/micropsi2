__author__ = 'rvuine'

import json
import os

import warnings
import micropsi_core
from micropsi_core.nodenet import monitor
from micropsi_core.nodenet.node import Nodetype
from micropsi_core.nodenet.nodenet import Nodenet, NODENET_VERSION, NodenetLockException
from micropsi_core.nodenet.stepoperators import DoernerianEmotionalModulators
from .dict_stepoperators import DictPropagate, DictPORRETDecay, DictCalculate
from .dict_node import DictNode
from .dict_nodespace import DictNodespace
import copy

STANDARD_NODETYPES = {
    "Nodespace": {
        "name": "Nodespace"
    },

    "Comment": {
        "name": "Comment",
        "symbol": "#",
        'parameters': ['comment'],
        "shape": "Rectangle"
    },

    "Register": {
        "name": "Register",
        "slottypes": ["gen"],
        "nodefunction_name": "register",
        "gatetypes": ["gen"]
    },
    "Sensor": {
        "name": "Sensor",
        "parameters": ["datasource"],
        "nodefunction_name": "sensor",
        "gatetypes": ["gen"]
    },
    "Actor": {
        "name": "Actor",
        "parameters": ["datatarget"],
        "nodefunction_name": "actor",
        "slottypes": ["gen"],
        "gatetypes": ["gen"]
    },
    "Concept": {
        "name": "Concept",
        "slottypes": ["gen"],
        "nodefunction_name": "concept",
        "gatetypes": ["gen", "por", "ret", "sub", "sur", "cat", "exp", "sym", "ref"]
    },
    "Script": {
        "name": "Script",
        "slottypes": ["gen", "por", "ret", "sub", "sur"],
        "nodefunction_name": "script",
        "gatetypes": ["gen", "por", "ret", "sub", "sur", "cat", "exp", "sym", "ref"],
        "gate_defaults": {
            "por": {
                "threshold": -1
            },
            "ret": {
                "threshold": -1
            },
            "sub": {
                "threshold": -1
            },
            "sur": {
                "threshold": -1
            }
        }
    },
    "Pipe": {
        "name": "Pipe",
        "slottypes": ["gen", "por", "ret", "sub", "sur", "cat", "exp"],
        "nodefunction_name": "pipe",
        "gatetypes": ["gen", "por", "ret", "sub", "sur", "cat", "exp"],
        "parameters": ["expectation", "wait"],
        "symbol": "πp",
        "shape": "Rectangle",
        "parameter_defaults": {
            "expectation": 1,
            "wait": 10
        }
    },
    "Activator": {
        "name": "Activator",
        "slottypes": ["gen"],
        "parameters": ["type"],
        "parameter_values": {"type": ["por", "ret", "sub", "sur", "cat", "exp", "sym", "ref"]},
        "nodefunction_name": "activator"
    }
}

class DictNodenet(Nodenet):
    """Main data structure for MicroPsi agents,

    Contains the net entities and runs the activation spreading. The nodenet stores persistent data.

    Attributes:
        state: a dict of persistent nodenet data; everything stored within the state can be stored and exported
        uid: a unique identifier for the node net
        name: an optional name for the node net
        nodespaces: a dictionary of node space UIDs and respective node spaces
        nodes: a dictionary of node UIDs and respective nodes
        links: a dictionary of link UIDs and respective links
        gate_types: a dictionary of gate type names and the individual types of gates
        slot_types: a dictionary of slot type names and the individual types of slots
        node_types: a dictionary of node type names and node type definitions
        world: an environment for the node net
        worldadapter: an actual world adapter object residing in a world implementation, provides interface
        owner: an id of the user who created the node net
        step: the current simulation step of the node net
    """

    @property
    def data(self):
        data = super(DictNodenet, self).data
        data['links'] = self.construct_links_dict()
        data['nodes'] = self.construct_nodes_dict()
        data['nodespaces'] = self.construct_nodespaces_dict("Root")
        data['version'] = self.__version
        data['modulators'] = self.construct_modulators_dict()
        return data

    @property
    def engine(self):
        return "dict_engine"

    @property
    def current_step(self):
        return self.__step

    def __init__(self, name="", worldadapter="Default", world=None, owner="", uid=None, native_modules={}):
        """Create a new MicroPsi agent.

        Arguments:
            agent_type (optional): the interface of this agent to its environment
            name (optional): the name of the agent
            owner (optional): the user that created this agent
            uid (optional): unique handle of the agent; if none is given, it will be generated
        """

        super(DictNodenet, self).__init__(name, worldadapter, world, owner, uid)

        self.stepoperators = [DictPropagate(), DictCalculate(), DictPORRETDecay(), DoernerianEmotionalModulators()]
        self.stepoperators.sort(key=lambda op: op.priority)

        self.__version = NODENET_VERSION  # used to check compatibility of the node net data
        self.__step = 0
        self.__modulators = {
            'por_ret_decay': 0.
        }

        if world and worldadapter:
            self.worldadapter = worldadapter

        self.__nodes = {}
        self.__nodespaces = {}
        self.__nodespaces["Root"] = DictNodespace(self, None, (0, 0), name="Root", uid="Root")

        self.__nodetypes = {}
        for type, data in STANDARD_NODETYPES.items():
            self.__nodetypes[type] = Nodetype(nodenet=self, **data)

        self.__native_modules = {}
        for type, data in native_modules.items():
            self.__native_modules[type] = Nodetype(nodenet=self, **data)

        self.nodegroups = {}

        self.initialize_nodenet({})

    def save(self, filename):
        # dict_engine saves metadata and data into the same json file, so just dump .data
        with open(filename, 'w+') as fp:
            fp.write(json.dumps(self.data, sort_keys=True, indent=4))
        if os.path.getsize(filename) < 100:
            # kind of hacky, but we don't really know what was going on
            raise RuntimeError("Error writing nodenet file")

    def load(self, filename):
        """Load the node net from a file"""
        # try to access file
        with self.netlock:

            initfrom = {}

            if os.path.isfile(filename):
                try:
                    self.logger.info("Loading nodenet %s from file %s", self.name, filename)
                    with open(filename) as file:
                        initfrom.update(json.load(file))
                except ValueError:
                    warnings.warn("Could not read nodenet data")
                    return False
                except IOError:
                    warnings.warn("Could not open nodenet file")

            if self.__version == NODENET_VERSION:
                self.initialize_nodenet(initfrom)
                return True
            else:
                raise NotImplementedError("Wrong version of nodenet data, cannot import.")

    def remove(self, filename):
        os.remove(filename)

    def reload_native_modules(self, native_modules):
        """ reloads the native-module definition, and their nodefunctions
        and afterwards reinstantiates the nodenet."""
        self.__native_modules = {}
        for key in native_modules:
            self.__native_modules[key] = Nodetype(nodenet=self, **native_modules[key])
        saved = self.data
        self.clear()
        self.merge_data(saved, keep_uids=True)

    def initialize_nodespace(self, id, data):
        if id not in self.__nodespaces:
            # move up the nodespace tree until we find an existing parent or hit root
            while id != 'Root' and data[id].get('parent_nodespace') not in self.__nodespaces:
                self.initialize_nodespace(data[id]['parent_nodespace'], data)
            self.__nodespaces[id] = DictNodespace(self,
                data[id].get('parent_nodespace'),
                data[id].get('position'),
                name=data[id].get('name', 'Root'),
                uid=id,
                index=data[id].get('index'))

    def initialize_nodenet(self, initfrom):
        """Called after reading new nodenet state.

        Parses the nodenet state and set up the non-persistent data structures necessary for efficient
        computation of the node net
        """

        self.__modulators = initfrom.get("modulators", {})

        # set up nodespaces; make sure that parent nodespaces exist before children are initialized
        self.__nodespaces = {}
        self.__nodespaces["Root"] = DictNodespace(self, None, (0, 0), name="Root", uid="Root")

        if len(initfrom) != 0:
            # now merge in all init data (from the persisted file typically)
            self.merge_data(initfrom, keep_uids=True)

    def construct_links_dict(self):
        data = {}
        for node_uid in self.get_node_uids():
            links = self.get_node(node_uid).get_associated_links()
            for link in links:
                data[link.uid] = link.data
        return data

    def construct_nodes_dict(self, max_nodes=-1):
        data = {}
        i = 0
        for node_uid in self.get_node_uids():
            i += 1
            data[node_uid] = self.get_node(node_uid).data
            if max_nodes > 0 and i > max_nodes:
                break
        return data

    def construct_nodespaces_dict(self, nodespace_uid):
        data = {}
        if nodespace_uid is None:
            nodespace_uid = "Root"
        for nodespace_candidate_uid in self.get_nodespace_uids():
            is_in_hierarchy = False
            if nodespace_candidate_uid == nodespace_uid:
                is_in_hierarchy = True
            else:
                parent_uid = self.get_nodespace(nodespace_candidate_uid).parent_nodespace
                while parent_uid is not None and parent_uid != nodespace_uid:
                    parent_uid = self.get_nodespace(parent_uid).parent_nodespace
                if parent_uid == nodespace_uid:
                    is_in_hierarchy = True

            if is_in_hierarchy:
                data[nodespace_candidate_uid] = self.get_nodespace(nodespace_candidate_uid).data
        return data

    def get_nodetype(self, type):
        """ Returns the nodetpype instance for the given nodetype or native_module or None if not found"""
        if type in self.__nodetypes:
            return self.__nodetypes[type]
        else:
            return self.__native_modules.get(type)

    def get_nodespace_data(self, nodespace, include_links):
        world_uid = self.world.uid if self.world is not None else None

        data = {
            'links': {},
            'nodes': {},
            'name': self.name,
            'max_coords': {'x': 0, 'y': 0},
            'is_active': self.is_active,
            'current_step': self.current_step,
            'nodespaces': self.construct_nodespaces_dict(nodespace),
            'world': world_uid,
            'worldadapter': self.worldadapter,
            'modulators': self.construct_modulators_dict()
        }
        if self.user_prompt is not None:
            data['user_prompt'] = self.user_prompt.copy()
            self.user_prompt = None
        links = []
        followupnodes = []
        for uid in self.__nodes:
            if self.get_node(uid).parent_nodespace == nodespace:  # maybe sort directly by nodespace??
                node = self.get_node(uid)
                data['nodes'][uid] = node.data
                if node.position[0] > data['max_coords']['x']:
                    data['max_coords']['x'] = node.position[0]
                if node.position[1] > data['max_coords']['y']:
                    data['max_coords']['y'] = node.position[1]
                if include_links:
                    links.extend(self.get_node(uid).get_associated_links())
                    followupnodes.extend(self.get_node(uid).get_associated_node_uids())
        if include_links:
            for link in links:
                data['links'][link.uid] = link.data
            for uid in followupnodes:
                if uid not in data['nodes']:
                    data['nodes'][uid] = self.get_node(uid).data
        return data

    def delete_node(self, node_uid):
        if node_uid in self.__nodespaces:
            affected_entity_ids = self.__nodespaces[node_uid].get_known_ids()
            for uid in affected_entity_ids:
                self.delete_node(uid)
            parent_nodespace = self.__nodespaces.get(self.__nodespaces[node_uid].parent_nodespace)
            if parent_nodespace and parent_nodespace.is_entity_known_as('nodespaces', node_uid):
                parent_nodespace._unregister_entity('nodespaces', node_uid)
            del self.__nodespaces[node_uid]
        else:
            node = self.__nodes[node_uid]
            node.unlink_completely()
            parent_nodespace = self.__nodespaces.get(self.__nodes[node_uid].parent_nodespace)
            parent_nodespace._unregister_entity('nodes', node_uid)
            if self.__nodes[node_uid].type == "Activator":
                parent_nodespace.unset_activator_value(self.__nodes[node_uid].get_parameter('type'))
            del self.__nodes[node_uid]

    def delete_nodespace(self, uid):
        self.delete_node(uid)

    def clear(self):
        super(DictNodenet, self).clear()
        self.__nodes = {}

        self.max_coords = {'x': 0, 'y': 0}

        self.__nodespaces = {}
        DictNodespace(self, None, (0, 0), "Root", "Root")

    def _register_node(self, node):
        self.__nodes[node.uid] = node

    def _register_nodespace(self, nodespace):
        self.__nodespaces[nodespace.uid] = nodespace

    def merge_data(self, nodenet_data, keep_uids=False):
        """merges the nodenet state with the current node net, might have to give new UIDs to some entities"""

        # merge in spaces, make sure that parent nodespaces exist before children are initialized
        nodespaces_to_merge = set(nodenet_data.get('nodespaces', {}).keys())
        for nodespace in nodespaces_to_merge:
            self.initialize_nodespace(nodespace, nodenet_data['nodespaces'])

        uidmap = {}

        # merge in nodes
        for uid in nodenet_data.get('nodes', {}):
            data = nodenet_data['nodes'][uid]
            if not keep_uids:
                newuid = micropsi_core.tools.generate_uid()
            else:
                newuid = uid
            data['uid'] = newuid
            uidmap[uid] = newuid
            if data['type'] in self.__nodetypes or data['type'] in self.__native_modules:
                self.__nodes[newuid] = DictNode(self, **data)
            else:
                warnings.warn("Invalid nodetype %s for node %s" % (data['type'], uid))

        # merge in links
        for linkid in nodenet_data.get('links', {}):
            data = nodenet_data['links'][linkid]
            self.create_link(
                uidmap[data['source_node_uid']],
                data['source_gate_name'],
                uidmap[data['target_node_uid']],
                data['target_slot_name'],
                data['weight']
            )

        for monitorid in nodenet_data.get('monitors', {}):
            data = nodenet_data['monitors'][monitorid]
            if 'node_uid' in data:
                old_node_uid = data['node_uid']
                if old_node_uid in uidmap:
                    data['node_uid'] = uidmap[old_node_uid]
            if 'classname' in data:
                if hasattr(monitor, data['classname']):
                    getattr(monitor, data['classname'])(self, **data)
                else:
                    self.logger.warn('unknown classname for monitor: %s (uid:%s) ' % (data['classname'], monitorid))
            else:
                # Compatibility mode
                monitor.NodeMonitor(self, name=data['node_name'], **data)

    def step(self):
        """perform a simulation step"""
        self.user_prompt = None
        if self.world is not None and self.world.agents is not None and self.uid in self.world.agents:
            self.world.agents[self.uid].snapshot()      # world adapter snapshot
                                                        # TODO: Not really sure why we don't just know our world adapter,
                                                        # but instead the world object itself

        with self.netlock:

            for operator in self.stepoperators:
                operator.execute(self, self.__nodes.copy(), self.netapi)

            self.__step += 1

    def create_node(self, nodetype, nodespace_uid, position, name="", uid=None, parameters=None, gate_parameters=None):
        nodespace_uid = self.get_nodespace(nodespace_uid).uid
        node = DictNode(
            self,
            nodespace_uid,
            position, name=name,
            type=nodetype,
            uid=uid,
            parameters=parameters,
            gate_parameters=gate_parameters)
        return node.uid

    def create_nodespace(self, parent_uid, position, name="", uid=None, options=None):
        parent_uid = self.get_nodespace(parent_uid).uid
        nodespace = DictNodespace(self, parent_uid, position=position, name=name, uid=uid)
        return nodespace.uid

    def get_node(self, uid):
        return self.__nodes[uid]

    def get_nodespace(self, uid):
        if uid is None:
            uid = "Root"
        return self.__nodespaces[uid]

    def get_node_uids(self, group_nodespace_uid=None, group=None):
        if group is not None:
            if group_nodespace_uid is None:
                group_nodespace_uid = self.get_nodespace(None).uid
            return [n.uid for n in self.nodegroups[group_nodespace_uid][group][0]]
        else:
            return list(self.__nodes.keys())

    def get_nodespace_uids(self):
        return list(self.__nodespaces.keys())

    def is_node(self, uid):
        return uid in self.__nodes

    def is_nodespace(self, uid):
        return uid in self.__nodespaces

    def get_nativemodules(self, nodespace=None):
        """Returns a dict of native modules. Optionally filtered by the given nodespace"""
        nodes = self.__nodes if nodespace is None else self.__nodespaces[nodespace].get_known_ids('nodes')
        nativemodules = {}
        for uid in nodes:
            if self.__nodes[uid].type not in STANDARD_NODETYPES:
                nativemodules.update({uid: self.__nodes[uid]})
        return nativemodules

    def get_activators(self, nodespace=None, type=None):
        """Returns a dict of activator nodes. OPtionally filtered by the given nodespace and the given type"""
        nodes = self.__nodes if nodespace is None else self.__nodespaces[nodespace].get_known_ids('nodes')
        activators = {}
        for uid in nodes:
            if self.__nodes[uid].type == 'Activator':
                if type is None or type == self.__nodes[uid].get_parameter('type'):
                    activators.update({uid: self.__nodes[uid]})
        return activators

    def get_sensors(self, nodespace=None, datasource=None):
        """Returns a dict of all sensor nodes. Optionally filtered by the given nodespace"""
        nodes = self.__nodes if nodespace is None else self.__nodespaces[nodespace].get_known_ids('nodes')
        sensors = {}
        for uid in nodes:
            if self.__nodes[uid].type == 'Sensor':
                if datasource is None or self.__nodes[uid].get_parameter('datasource') == datasource:
                    sensors[uid] = self.__nodes[uid]
        return sensors

    def get_actors(self, nodespace=None, datatarget=None):
        """Returns a dict of all sensor nodes. Optionally filtered by the given nodespace"""
        nodes = self.__nodes if nodespace is None else self.__nodespaces[nodespace].get_known_ids('nodes')
        actors = {}
        for uid in nodes:
            if self.__nodes[uid].type == 'Actor':
                if datatarget is None or self.__nodes[uid].get_parameter('datatarget') == datatarget:
                    actors[uid] = self.__nodes[uid]
        return actors

    def set_link_weight(self, source_node_uid, gate_type, target_node_uid, slot_type, weight=1, certainty=1):
        """Set weight of the given link."""

        source_node = self.get_node(source_node_uid)
        if source_node is None:
            return False

        link = source_node.link(gate_type, target_node_uid, slot_type, weight, certainty)
        if link is None:
            return False
        else:
            return True

    def create_link(self, source_node_uid, gate_type, target_node_uid, slot_type, weight=1, certainty=1):
        """Creates a new link.

        Arguments.
            source_node_uid: uid of the origin node
            gate_type: type of the origin gate (usually defines the link type)
            target_node_uid: uid of the target node
            slot_type: type of the target slot
            weight: the weight of the link (a float)
            certainty (optional): a probabilistic parameter for the link

        Returns:
            the link if successful,
            None if failure
        """

        source_node = self.get_node(source_node_uid)
        if source_node is None:
            return False, None

        source_node.link(gate_type, target_node_uid, slot_type, weight, certainty)
        return True

    def delete_link(self, source_node_uid, gate_type, target_node_uid, slot_type):
        """Delete the given link."""

        source_node = self.get_node(source_node_uid)
        if source_node is None:
            return False, None
        source_node.unlink(gate_type, target_node_uid, slot_type)
        return True

    def get_modulator(self, modulator):
        """
        Returns the numeric value of the given global modulator
        """
        return self.__modulators.get(modulator, 1)

    def change_modulator(self, modulator, diff):
        """
        Changes the value of the given global modulator by the value of diff
        """
        self.__modulators[modulator] = self.__modulators.get(modulator, 0) + diff

    def construct_modulators_dict(self):
        """
        Returns a new dict containing all modulators
        """
        return self.__modulators.copy()

    def set_modulator(self, modulator, value):
        """
        Changes the value of the given global modulator to the given value
        """
        self.__modulators[modulator] = value

    def get_standard_nodetype_definitions(self):
        """
        Returns the standard node types supported by this nodenet
        """
        return copy.deepcopy(STANDARD_NODETYPES)

    def group_nodes_by_names(self, nodespace_uid, node_name_prefix=None, gatetype="gen", sortby='id'):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if nodespace_uid not in self.nodegroups:
            self.nodegroups[nodespace_uid] = {}

        nodes = self.netapi.get_nodes(nodespace_uid, node_name_prefix)
        if sortby == 'id':
            nodes = sorted(nodes, key=lambda node: node.uid)
        elif sortby == 'name':
            nodes = sorted(nodes, key=lambda node: node.name)
        self.nodegroups[nodespace_uid][node_name_prefix] = (nodes, gatetype)

    def group_nodes_by_ids(self, nodespace_uid, node_uids, group_name, gatetype="gen", sortby='id'):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if nodespace_uid not in self.nodegroups:
            self.nodegroups[nodespace_uid] = {}

        nodes = []
        for node_uid in node_uids:
            node = self.get_node(node_uid)
            if node.parent_nodespace != nodespace_uid:
                raise ValueError("Node %s is not in nodespace %s" % (node_uid, nodespace_uid))
            nodes.append(node)
        if sortby == 'id':
            nodes = sorted(nodes, key=lambda node: node.uid)
        elif sortby == 'name':
            nodes = sorted(nodes, key=lambda node: node.name)
        self.nodegroups[nodespace_uid][group_name] = (nodes, gatetype)

    def ungroup_nodes(self, nodespace_uid, group):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if group in self.nodegroups:
            del self.nodegroups[nodespace_uid][group]

    def get_activations(self, nodespace_uid, group):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if group not in self.nodegroups[nodespace_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group, nodespace_uid))
        activations = []
        nodes = self.nodegroups[nodespace_uid][group][0]
        gate = self.nodegroups[nodespace_uid][group][1]
        for node in nodes:
            activations.append(node.get_gate(gate).activation)
        return activations

    def set_activations(self, nodespace_uid, group, new_activations):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if group not in self.nodegroups[nodespace_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group, nodespace_uid))
        nodes = self.nodegroups[nodespace_uid][group][0]
        gate = self.nodegroups[nodespace_uid][group][1]
        for i in range(len(nodes)):
            nodes[i].set_gate_activation(gate, new_activations[i])

    def get_thetas(self, nodespace_uid, group):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if group not in self.nodegroups[nodespace_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group, nodespace_uid))
        thetas = []
        nodes = self.nodegroups[nodespace_uid][group][0]
        gate = self.nodegroups[nodespace_uid][group][1]
        for node in nodes:
            thetas.append(node.get_gate(gate).get_parameter('theta'))
        return thetas

    def set_thetas(self, nodespace_uid, group, thetas):
        if nodespace_uid is None:
            nodespace_uid = self.get_nodespace(None).uid

        if group not in self.nodegroups[nodespace_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group, nodespace_uid))
        nodes = self.nodegroups[nodespace_uid][group][0]
        gate = self.nodegroups[nodespace_uid][group][1]
        for i in range(len(nodes)):
            nodes[i].set_gate_parameter(gate, 'theta', thetas[i])

    def get_link_weights(self, nodespace_from_uid, group_from, nodespace_to_uid, group_to):
        if nodespace_from_uid is None:
            nodespace_from_uid = self.get_nodespace(None).uid
        if nodespace_to_uid is None:
            nodespace_to_uid = self.get_nodespace(None).uid

        if group_from not in self.nodegroups[nodespace_from_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group_from, nodespace_from_uid))
        if group_to not in self.nodegroups[nodespace_to_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group_to, nodespace_to_uid))
        rows = []
        to_nodes = self.nodegroups[nodespace_to_uid][group_to][0]
        to_slot = self.nodegroups[nodespace_to_uid][group_to][1]
        from_nodes = self.nodegroups[nodespace_from_uid][group_from][0]
        from_gate = self.nodegroups[nodespace_from_uid][group_from][1]
        for to_node in to_nodes:
            row = []
            for from_node in from_nodes:
                links = from_node.get_gate(from_gate).get_links()
                hit = None
                for link in links:
                    if link.target_node == to_node and link.target_slot.type == to_slot:
                        hit = link
                        break
                if hit is not None:
                    row.append(link.weight)
                else:
                    row.append(0)
            rows.append(row)
        return rows

    def set_link_weights(self, nodespace_from_uid, group_from, nodespace_to_uid, group_to, new_w):
        if nodespace_from_uid is None:
            nodespace_from_uid = self.get_nodespace(None).uid
        if nodespace_to_uid is None:
            nodespace_to_uid = self.get_nodespace(None).uid

        if group_from not in self.nodegroups[nodespace_from_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group_from, nodespace_from_uid))
        if group_to not in self.nodegroups[nodespace_to_uid]:
            raise ValueError("Group %s does not exist in nodespace %s" % (group_to, nodespace_to_uid))
        to_nodes = self.nodegroups[nodespace_to_uid][group_to][0]
        to_slot = self.nodegroups[nodespace_to_uid][group_to][1]
        from_nodes = self.nodegroups[nodespace_from_uid][group_from][0]
        from_gate = self.nodegroups[nodespace_from_uid][group_from][1]
        for row in range(len(to_nodes)):
            to_node = to_nodes[row]
            for column in range(len(from_nodes)):
                from_node = from_nodes[column]
                weight = new_w[row][column]
                if weight != 0:
                    self.set_link_weight(from_node.uid, from_gate, to_node.uid, to_slot, weight)
                else:
                    self.delete_link(from_node.uid, from_gate, to_node.uid, to_slot)

    def get_available_gatefunctions(self):
        """
        Returns a list of available gate functions
        """
        from inspect import getmembers, isfunction
        from micropsi_core.nodenet import gatefunctions
        return sorted([name for name, func in getmembers(gatefunctions, isfunction)])
