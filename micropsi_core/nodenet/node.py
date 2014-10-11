# -*- coding: utf-8 -*-

"""
Node definition

Gate definition
Slot definition
Nodetype definition

default Nodetypes

"""

import warnings
import micropsi_core.tools
from .netentity import *
import logging

__author__ = 'joscha'
__date__ = '09.05.12'

class SheafElement:
    def __init__(self, uid="default", name="default", activation=0):
        self.uid = uid
        self.name = name
        self.activation = activation

    @property
    def activation(self):
        return self._activation

    @activation.setter
    def activation(self, activation):
        if activation==1:
            print("boo")
        self._activation = activation

    def copy(self):
        return SheafElement(uid=self.uid, name=self.name)

class LinkData(object):
    def __init__(self):
        self.weight = 0
        self.certainty = 0

class LinkProxy(BasicNetEntity):
    @property
    def source_gate(self):
        return self.source_node.get_gate(self.source_gate_type)

    @property
    def target_slot(self):
        return self.target_node.get_slot(self.target_slot_type)

    @property
    def _weight(self):
        return self.weight

    @property
    def _certainty(self):
        return self.certainty

    @property
    def _source_gate_name(self):
        return self.source_gate_type

    @property
    def _target_slot_name(self):
        return self.target_slot_type

    @property
    def _source_node_uid(self):
        return self.source_node.uid

    @property
    def _target_node_uid(self):
        return self.target_node.uid

    def get_data_properties(self):
        return [ 'source_node_uid', 'target_node_uid', 'weight', 'certainty', 'source_gate_name', 'target_slot_name']

    def __init__(self, source_node, source_gate_type, target_node, target_slot_type, weight=1, certainty=1):

        self.source_node = source_node
        self.source_gate_type = source_gate_type
        self.target_node = target_node
        self.target_slot_type = target_slot_type
        self.weight = weight
        self.certainty = certainty

class NodeData:
    pass

class Node(NetEntity):
    """A net entity with slots and gates and a node function.

    Node functions are called alternating with the link functions. They process the information in the slots
    and usually call all the gate functions to transmit the activation towards the links.

    Attributes:
        activation: a numeric value (usually between -1 and 1) to indicate its activation. Activation is determined
            by the node function, usually depending on the value of the slots.
        slots: a list of slots (activation inlets)
        gates: a list of gates (activation outlets)
        node_function: a function to be executed whenever the node receives activation
    """

    def get_data_properties(self):
        return ['uid', 'index', 'name', 'position', 'parent_nodespace', 'type', 'parameters', 'gate_parameters',
            'gate_activations', 'state']

    @property
    def activation(self):
        return self.sheaves['default'].activation

    @activation.setter
    def activation(self, activation):
        self.set_sheaf_activation(activation)

    def set_sheaf_activation(self, activation, sheaf="default"):
        sheaves_to_calculate = self.get_sheaves_to_calculate()
        if sheaf not in sheaves_to_calculate:
            raise "Sheaf " + sheaf + " can not be set as it hasn't been propagated to any slot"

        if activation is None: activation = 0

        self.sheaves[sheaf].activation = float(activation)
        # self.sheaves[sheaf] = {"uid": sheaf, "name": sheaves_to_calculate[sheaf].name, "activation": activation}
        if len(self.nodetype.gatetypes):
            self.set_gate_activation(self.nodetype.gatetypes[0], activation, sheaf)\

    @property
    def slots(self):
        return self.error

    def get_gate_link_data(self,gate_type,target_node,slot_type):
        gateToSlotMap = self._gate_links_to_data.get(gate_type, None)
        if gateToSlotMap is None:
            return None
        slotToNodeMap = gateToSlotMap.get(slot_type,None)
        if slotToNodeMap is None:
            return None
        linkData = slotToNodeMap.get(target_node,None)
        return linkData

    def get_or_create_gate_link_data(self,gate_type,target_node,slot_type):
        gateToSlotMap = self._gate_links_to_data.get(gate_type, None)
        if gateToSlotMap is None:
            gateToSlotMap = {}
            self._gate_links_to_data[gate_type] = gateToSlotMap
        slotToNodeMap = gateToSlotMap.get(slot_type,None)
        if slotToNodeMap is None:
            slotToNodeMap = {}
            gateToSlotMap[slot_type] = slotToNodeMap
        linkData = slotToNodeMap.get(target_node,None)
        if linkData is None:
            linkData = LinkData()
            slotToNodeMap[target_node] = linkData
        return linkData

    def remove_gate_link_data(self,gate_type,target_node,slot_type):
        gateToSlotMap = self._gate_links_to_data.get(gate_type, None)
        if gateToSlotMap is None:
            return None
        slotToNodeMap = gateToSlotMap.get(slot_type,None)
        if slotToNodeMap is None:
            return None
        slotToNodeMap.pop( target_node, None)

    def get_slot_links_with_gate(self,slot_type,gate_type):
        slotToGateMap = self._slot_links_to_node.get(slot_type, None)
        if slotToGateMap is None:
            return None
        nodeSet = slotToGateMap.get(gate_type,None)
        if nodeSet is None:
            return None
        return nodeSet

    def get_or_create_slot_links(self,slot_type,gate_type):
        slotToGateMap = self._slot_links_to_node.get(slot_type, None)
        if slotToGateMap is None:
            slotToGateMap = {}
            self._slot_links_to_node[slot_type] = slotToGateMap
        nodeSet = slotToGateMap.get(gate_type,None)
        if nodeSet is None:
            nodeSet = set()
            slotToGateMap[gate_type] = nodeSet
        return nodeSet

    def get_slot_links(self, slot_type):
        links = []
        slotToGateMap = self._slot_links_to_node.get(slot_type, None)
        if slotToGateMap is None:
            return links
        for gate_type, nodeSet in slotToGateMap.items():
            for source_node in nodeSet:
                weight = source_node.get_link_weight( gate_type, slot_type, self )
                certainty = source_node.get_link_certainty( gate_type, slot_type, self )
                links.append( LinkProxy( source_node, gate_type, self, slot_type, weight, certainty ))
        return links

    def add_slot_link(self,slot_type,source_node,gate_type):
        nodeSet = self.get_or_create_slot_links(slot_type,gate_type)
        nodeSet.add(source_node)

    def remove_slot_link(self,slot_type,source_node,gate_type):
        nodeSet = self.get_or_create_slot_links(slot_type,gate_type)
        nodeSet.remove(source_node)

    def get_link_weight(self,gate_type,target_node,slot_type):
        linkData = self.get_gate_link_data(gate_type,target_node,slot_type)
        if linkData is None:
            return None
        return linkData.weight

    def get_link_certainty(self,gate_type,target_node,slot_type):
        linkData = self.get_gate_link_data(gate_type,target_node,slot_type)
        if linkData is None:
            return None
        return linkData.certainty

    def set_link_weight(self,gate_type,target_node,slot_type,weight):
        linkData = self.get_or_create_gate_link_data(gate_type,target_node,slot_type)
        linkData.weight = weight

    def set_link_certainty(self,gate_type,target_node,slot_type,certainty):
        linkData = self.get_or_create_gate_link_data(gate_type,target_node,slot_type)
        linkData.certainty = certainty

    def get_gate_links(self, gate_type):
        links = []
        gateToSlotMap = self._gate_links_to_data.get(gate_type, None)
        if gateToSlotMap is None:
            return links
        for slot_type, nodeMap in gateToSlotMap.items():
            for node, linkdata in nodeMap.items():
                links.append( LinkProxy( self, gate_type, node, slot_type, linkdata.weight, linkdata.certainty ))
        return links

    def get_gate_link(self, gate_type, target_node, slot_type):
        linkdata = self.get_gate_link_data(gate_type,target_node,slot_type)
        return LinkProxy( self, gate_type, target_node, slot_type, linkdata.weight, linkdata.certainty )

    def get_slot_types(self):
        return self._slot_sheaves.keys()

    def get_gate_types(self):
        return self._gate_sheaves.keys()

    def get_gate_specific_parameters(self,linktype):
        gateParameters = self._gate_parameters.get(linktype,None)
        if gateParameters is None:
            gateParameters = {}
            self._gate_parameters[linktype] = gateParameters
        return gateParameters

    def set_gate_specific_parameters(self,linktype,parameters):
        gateParameters = self._gate_parameters.get(linktype,None)
        if gateParameters is None:
            gateParameters = {}
            self._gate_parameters[linktype] = gateParameters
        gateParameters.clear()
        gateParameters.update( parameters )

    def get_slot_sheaves(self, linktype):
        sheaves = self._slot_sheaves.get(linktype,None)
        if sheaves is None:
            sheaves = {}
            self._slot_sheaves[linktype] = sheaves
        return sheaves

    def get_gate_sheaves(self, linktype):
        sheaves = self._gate_sheaves.get(linktype,None)
        if sheaves is None:
            sheaves = {}
            self._gate_sheaves[linktype] = sheaves
        return sheaves

    def initialize_slot_sheaves(self, linktype):
        sheaves = self.get_slot_sheaves(linktype)
        sheaves.clear()
        sheaves["default"] = SheafElement()

    def add_slot(self, linktype):
        self.get_slot_sheaves(linktype)

    def add_gate(self, linktype):
        self.get_gate_sheaves(linktype)
        self.report_gate_activation(linktype, self.get_gate_sheaf(linktype,'default'))

    def get_slot_sheaf(self, linktype, sheaf):
        sheaves = self.get_slot_sheaves(linktype)
        sheafElement = sheaves.get(sheaf,None)
        if sheafElement is None:
            sheafElement = SheafElement()
            sheaves[sheaf] = sheafElement
        return sheafElement

    def get_gate_sheaf(self, linktype, sheaf):
        sheaves = self.get_gate_sheaves(linktype)
        sheafElement = sheaves.get(sheaf,None)
        if sheafElement is None:
            sheafElement = SheafElement()
            sheaves[sheaf] = sheafElement
        return sheafElement

    def unlink_all(self):
        self.unlink_all_gates()
        self.unlink_all_slots()

    def unlink_gate(self,gate_type):
        gate = self.get_gate(gate_type)
        for link in gate.outgoing:
            self.unlink(link.source_gate_type, link.target_node, link.target_slot_type)

    def unlink_all_gates(self):
        for gate_type, gateToSlotMap in self._gate_links_to_data.items():
            for slot_type, nodeMap in gateToSlotMap.items():
                for target_node, linkdata in nodeMap.items():
                    target_node.remove_slot_link(slot_type,self,gate_type)
        self._gate_links_to_data = {}

    def unlink(self,gate_type,target_node,slot_type):
        self.remove_gate_link_data(gate_type,target_node,slot_type)
        target_node.remove_slot_link(slot_type,self,gate_type)

    def unlink_all_slots(self):
        for slot_type, slotToGateMap in self._slot_links_to_node.items():
            for gate_type, nodeSet in slotToGateMap.items():
                for source_node in nodeSet:
                    source_node.remove_gate_link_data(gate_type,self,slot_type)
        self._slot_links_to_node = {}

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self,type):
        self._type = type

    @property
    def nodetype(self):
        return self.nodenet.get_nodetype(self.type)

    @property
    def parameters(self):
        return self._parameters

    @parameters.setter
    def parameters(self, dictionary):
        if self.type == "Native":
            self.nodetype.parameters = list(dictionary.keys())
        self._parameters = dictionary

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def gate_activations(self):
        return self._gate_activations

    @gate_activations.setter
    def gate_activations(self,gate_activations):
        self._gate_activations = gate_activations

    def init(self, nodenet, parent_nodespace, position, state=None, activation=0,
                 name="", type="Concept", uid=None, index=None, parameters=None, gate_parameters=None, gate_activations=None, **_):
        if not gate_parameters:
            gate_parameters = {}

        if uid in nodenet.nodes:
            raise KeyError("Node already exists")

        NetEntity_class().init(self, nodenet, parent_nodespace, position,
            name=name, entitytype="nodes", uid=uid, index=index)

        # self.gates = {}
        # self.slots = {}
        self.gate_activations = {}
        self._slot_links_to_node = {}
        self._slot_sheaves = {}
        self._gate_links_to_data = {}
        self._gate_sheaves = {}
        self._gate_parameters = {}
        self.type = type

        nodetype = nodenet.get_nodetype(type)
        self.parameters = dict((key, None) for key in nodetype.parameters)
        if parameters is not None:
            self.parameters.update(parameters)
        #self.gate_parameters = {}
        for gate in nodetype.gatetypes:
            if gate_activations is None or gate not in gate_activations:
                sheaves_to_use = None
            else:
                sheaves_to_use = gate_activations[gate]
            #self.gates[gate] = Gate_class().new(nodenet, gate, self, sheaves=sheaves_to_use, gate_function=None, parameters=gate_parameters.get(gate), gate_defaults=self.nodetype.gate_defaults[gate])
            #self.gate_parameters[gate] = self.gates[gate].parameters
            self.add_gate(gate)
            self.get_gate(gate).set_gate_parameters( gate_parameters.get(gate), nodetype.gate_defaults[gate] )
        for slot in nodetype.slottypes:
            self.add_slot(slot)
        if state:
            self.state = state
            # TODO: @doik: before, you explicitly added the state to nodenet.nodes[uid], too (in Runtime). Any reason?
        nodenet.nodes[self.uid] = self
        self.sheaves = {"default": SheafElement(activation=activation)}


    def get_gate_parameters(self):
        """Looks into the gates and returns gate parameters if these are defined"""
        gate_parameters = {}
        for gate_type in self.get_gate_types():
            gate_parameters.update(self.get_gate_specific_parameters(gate_type))
        if len(gate_parameters):
            return gate_parameters
        else:
            return None

    def set_gate_activation(self, gate_type, activation, sheaf="default"):
        """ sets the activation of the given gate, and calls `report_gate_activation`"""
        activation = float(activation)
        if gate_type in self.get_gate_types():
            sheafElement = self.get_gate_sheaf(gate_type,sheaf)
            sheafElement.activation = activation
            self.report_gate_activation(gate_type, sheafElement)

    def node_function(self):
        """Called whenever the node is activated or active.

        In different node types, different node functions may be used, i.e. override this one.
        Generally, a node function must process the slot activations and call each gate function with
        the result of the slot activations.

        Metaphorically speaking, the node function is the soma of a MicroPsi neuron. It reacts to
        incoming activations in an arbitrarily specific way, and may then excite the outgoing dendrites (gates),
        which transmit activation to other neurons with adaptive synaptic strengths (link weights).
        """

        # call nodefunction of my node type
        if self.nodetype and self.nodetype.nodefunction is not None:

            sheaves_to_calculate = self.get_sheaves_to_calculate()

            # find node activation to carry over
            node_activation_to_carry_over= {}
            for id in self.sheaves.keys():
                if id in sheaves_to_calculate:
                    node_activation_to_carry_over[id] = self.sheaves[id]

            # clear activation states
            for gate_type in self.get_gate_types():
                gate = self.get_gate(gate_type)
                gate.sheaves.clear()
                self.gate_activations[gate_type] = {}
            self.sheaves = {}

            # calculate activation states for all open sheaves
            for sheaf_id in sheaves_to_calculate.keys():

                # prepare sheaves
                for gatename in self.get_gate_types():
                    gate = self.get_gate(gatename)
                    gate.sheaves[sheaf_id] = sheaves_to_calculate[sheaf_id].copy()
                    gate.node.report_gate_activation(gate.type, gate.sheaves[sheaf_id])
                if sheaf_id in node_activation_to_carry_over:
                    self.sheaves[sheaf_id] = node_activation_to_carry_over[sheaf_id].copy()
                    self.set_sheaf_activation(node_activation_to_carry_over[sheaf_id].activation, sheaf_id)
                else:
                    self.sheaves[sheaf_id] = sheaves_to_calculate[sheaf_id].copy()
                    self.set_sheaf_activation(0, sheaf_id)

                # and actually calculate new values for them
                try:
                    self.nodetype.nodefunction(netapi=self.nodenet.netapi, node=self, sheaf=sheaf_id, **self.parameters)
                except Exception as err:
                    self.nodenet.is_active = False
                    self.activation = -1
                    raise err
        else:
            # default node function (only using the "default" sheaf)
            if len(self.slots):
                self.activation = sum([self.slots[slot].activation for slot in self.slots])
                if len(self.gates):
                    for type, gate in self.gates.items():
                        gate.gate_function(self.activation)

    def get_gate(self, gatename):
        return GateProxy( gatename, self )
        #return self.gates.get(gatename)

    def get_slot(self, slotname):
        return SlotProxy( slotname, self )
        #return self.slots.get(slotname)

    def get_associated_link_ids(self):
        links = []
        for key in self.gates:
            links.extend(self.gates[key].outgoing)
        for key in self.slots:
            links.extend(self.slots[key].incoming)
        return links

    def get_associated_node_ids(self):
        nodes = []
        for link in self.get_associated_link_ids():
            if self.nodenet.links[link].source_node.uid != self.uid:
                nodes.append(self.nodenet.links[link].source_node.uid)
            if self.nodenet.links[link].target_node.uid != self.uid:
                nodes.append(self.nodenet.links[link].target_node.uid)
        return nodes

    def get_sheaves_to_calculate(self):
        sheaves_to_calculate = {}
        for slotname in self.get_slot_types():
            slot = self.get_slot(slotname)
            for uid in slot.sheaves.keys():
                sheaves_to_calculate[uid] = slot.sheaves[uid].copy()
        if 'default' not in sheaves_to_calculate.keys():
            sheaves_to_calculate['default'] = SheafElement()
        return sheaves_to_calculate

    def set_gate_parameter(self, gate_type, parameter_name, parameter_value):
        gate_parameters = self.get_gate_specific_parameters(gate_type)
        gate_parameters[parameter_name] = parameter_value

    def get_gate_parameter(self, gate_type, parameter_name):
        return self.get_gate_specific_parameters(gate_type).get(parameter_name)

    def set_gate_parameters(self, gate_type, parameters):
        for parameter, value in parameters.items():
            if(parameter in Nodetype.GATE_DEFAULTS.keys()):
                try:
                    value = float(value)
                except:
                    raise Exception("Standard gate parameters must be numeric")
            self.set_gate_parameter( gate_type, parameter, value )

    def report_gate_activation(self, gate_type, sheafelement):
        if self.gate_activations is None:
            self.gate_activations = {}
        if gate_type not in self.gate_activations:
            self.gate_activations[gate_type] = {}
        if sheafelement.uid not in self.gate_activations[gate_type]:
            self.gate_activations[gate_type][sheafelement.uid] = {}
        self.gate_activations[gate_type][sheafelement.uid] = {"uid": sheafelement.uid, "name": sheafelement.name, "activation": sheafelement.activation}

    def reset_slots(self):
        for slotname in self.get_slot_types():
            self.get_slot(slotname).initialize_sheaves()

    def get_parameter(self, parameter):
        if parameter in self.parameters:
            return self.parameters[parameter]
        else:
            return None

    def clear_parameter(self, parameter):
        if parameter in self.parameters:
            if parameter not in self.nodetype.parameters:
                del self.parameters[parameter]
            else:
                self.parameters[parameter] = None

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def set_parameters(self, parameters):
        for key in parameters:
            self.set_parameter(key, parameters[key])

    def get_state(self, state_element):
        if state_element in self.state:
            return self.state[state_element]
        else:
            return None

    def set_state(self, state_element, value):
        if 'state' not in self.data:
            self.data['state'] = {}
        self.data['state'][state_element] = value

_Node_class = Node

def Node_class():
    return _Node_class

def set_Node_class(newClass):
    global _Node_class
    _Node_class = newClass


class GateProxy(object):
    def __init__(self, type, node):

        self.type = type
        self.node = node

    @property
    def activation(self):
        return self.get_activation("default")

    @property
    def outgoing(self):
        return self.node.get_gate_links(self.type)

    def get_activation(self, sheaf="default"):
        return self.node.get_gate_sheaf(self.type, sheaf).activation

    @property
    def sheaves(self):
        return self.node.get_gate_sheaves(self.type)

    @property
    def parameters(self):
        return self.node.get_gate_specific_parameters(self.type)

    @parameters.setter
    def parameters(self,parameters):
        return self.node.set_gate_specific_parameters(self.type,parameters)

    @sheaves.setter
    def sheaves(self,newValue):
        self.error

    def initialize_sheaves(self):
        self.node.initialize_gate_sheaves(self.type)

    def gate_function(self, input_activation, sheaf="default"):
        """This function sets the activation of the gate.

        The gate function should be called by the node function, and can be replaced by different functions
        if necessary. This default gives a linear function (input * amplification), cut off below a threshold.
        You might want to replace it with a radial basis function, for instance.
        """
        if input_activation is None: input_activation = 0


        # check if the current node space has an activator that would prevent the activity of this gate
        nodespace = self.node.nodenet.nodespaces[self.node.parent_nodespace]
        if self.type in nodespace.activators:
            gate_factor = nodespace.activators[self.type]
        else:
            gate_factor = 1.0
        if gate_factor == 0.0:
            self.sheaves[sheaf].activation = 0
            self.node.report_gate_activation(self.type, self.sheaves[sheaf])
            return  # if the gate is closed, we don't need to execute the gate function
            # simple linear threshold function; you might want to use a sigmoid for neural learning
        gatefunction = self.node.nodenet.nodespaces[self.node.parent_nodespace].get_gatefunction(self.node.type,
            self.type)
        if gatefunction:
            activation = gatefunction(input_activation, self.parameters.get('rho', 0), self.parameters.get('theta', 0))
        else:
            activation = input_activation

        if activation * gate_factor < self.parameters['threshold']:
            activation = 0
        else:
            activation = activation * self.parameters["amplification"] * gate_factor

        # if self.parameters["decay"]:  # let activation decay gradually
        #     if activation < 0:
        #         activation = min(activation, self.activation * (1 - self.parameters["decay"]))
        #     else:
        #         activation = max(activation, self.activation * (1 - self.parameters["decay"]))

        self.sheaves[sheaf].activation = min(self.parameters["maximum"], max(self.parameters["minimum"], activation))
        self.node.report_gate_activation(self.type, self.sheaves[sheaf])

    def open_sheaf(self, input_activation, sheaf="default"):
        """This function opens a new sheaf and calls the gate function for the newly opened sheaf
        """
        if sheaf is "default":
            sheaf_uid_prefix = "default" + "-"
            sheaf_name_prefix = ""
        else:
            sheaf_uid_prefix = sheaf + "-"
            sheaf_name_prefix = self.sheaves[sheaf].name + "-"

        new_sheaf = SheafElement(uid=sheaf_uid_prefix + self.node.uid, name=sheaf_name_prefix + self.node.name)
        self.sheaves[new_sheaf.uid] = new_sheaf

        self.gate_function(input_activation, new_sheaf.uid)


    def set_gate_parameters(self, parameters=None, gate_defaults=None):
        if gate_defaults is not None:
            self.node.set_gate_specific_parameters(self.type, gate_defaults.copy())
        if parameters is not None:
            for key in parameters:
                if key in Nodetype.GATE_DEFAULTS.keys():
                    try:
                        self.parameters[key] = float(parameters[key])
                    except:
                        logging.getLogger('nodenet').warn('Invalid gate parameter value for gate %s, param %s, node %s' % (type, key, self.node.uid))
                        self.parameters[key] = Nodetype.GATE_DEFAULTS.get(key, 0)
                else:
                    self.parameters[key] = float(parameters[key])


class Gate(object):  # todo: take care of gate functions at the level of nodespaces, handle gate params
    """The activation outlet of a node. Nodes may have many gates, from which links originate.

    Attributes:
        type: a string that determines the type of the gate
        node: the parent node of the gate
        activation: a numerical value which is calculated at every step by the gate function
        parameters: a dictionary of values used by the gate function
        gate_function: called by the node function, updates the activation
        outgoing: the set of links originating at the gate
    """


    @property
    def activation(self):
        return self.sheaves['default'].activation

    def init(self, nodenet, type, node, sheaves=None, gate_function=None, parameters=None, gate_defaults=None):
        """create a gate.

        Parameters:
            type: a string that refers to a node type
            node: the parent node
            parameters: an optional dictionary of parameters for the gate function
        """
        self.type = type
        self.node = node
        if sheaves is None:
            self.sheaves = {"default": SheafElement()}
        else:
            self.sheaves = {}
            for key in sheaves:
                self.sheaves[key] = SheafElement(uid=sheaves[key]['uid'], name=sheaves[key]['name'], activation=sheaves[key]['activation'])
        self.node.report_gate_activation(self.type, self.sheaves['default'])
        self.outgoing = {}
        self.gate_function = gate_function or self.gate_function
        self.parameters = {}
        if gate_defaults is not None:
            self.parameters = gate_defaults.copy()
        if parameters is not None:
            for key in parameters:
                if key in Nodetype.GATE_DEFAULTS.keys():
                    try:
                        self.parameters[key] = float(parameters[key])
                    except:
                        logging.getLogger('nodenet').warn('Invalid gate parameter value for gate %s, param %s, node %s' % (type, key, node.uid))
                        self.parameters[key] = Nodetype.GATE_DEFAULTS.get(key, 0)
                else:
                    self.parameters[key] = float(parameters[key])
        self.monitor = None

    def gate_function(self, input_activation, sheaf="default"):
        """This function sets the activation of the gate.

        The gate function should be called by the node function, and can be replaced by different functions
        if necessary. This default gives a linear function (input * amplification), cut off below a threshold.
        You might want to replace it with a radial basis function, for instance.
        """
        if input_activation is None: input_activation = 0


        # check if the current node space has an activator that would prevent the activity of this gate
        nodespace = self.node.nodenet.nodespaces[self.node.parent_nodespace]
        if self.type in nodespace.activators:
            gate_factor = nodespace.activators[self.type]
        else:
            gate_factor = 1.0
        if gate_factor == 0.0:
            self.sheaves[sheaf].activation = 0
            self.node.report_gate_activation(self.type, self.sheaves[sheaf])
            return  # if the gate is closed, we don't need to execute the gate function
            # simple linear threshold function; you might want to use a sigmoid for neural learning
        gatefunction = self.node.nodenet.nodespaces[self.node.parent_nodespace].get_gatefunction(self.node.type,
            self.type)
        if gatefunction:
            activation = gatefunction(input_activation, self.parameters.get('rho', 0), self.parameters.get('theta', 0))
        else:
            activation = input_activation

        if activation * gate_factor < self.parameters['threshold']:
            activation = 0
        else:
            activation = activation * self.parameters["amplification"] * gate_factor

        # if self.parameters["decay"]:  # let activation decay gradually
        #     if activation < 0:
        #         activation = min(activation, self.activation * (1 - self.parameters["decay"]))
        #     else:
        #         activation = max(activation, self.activation * (1 - self.parameters["decay"]))

        self.sheaves[sheaf].activation = min(self.parameters["maximum"], max(self.parameters["minimum"], activation))
        self.node.report_gate_activation(self.type, self.sheaves[sheaf])

    def open_sheaf(self, input_activation, sheaf="default"):
        """This function opens a new sheaf and calls the gate function for the newly opened sheaf
        """
        if sheaf is "default":
            sheaf_uid_prefix = "default" + "-"
            sheaf_name_prefix = ""
        else:
            sheaf_uid_prefix = sheaf + "-"
            sheaf_name_prefix = self.sheaves[sheaf].name + "-"

        new_sheaf = SheafElement(uid=sheaf_uid_prefix + self.node.uid, name=sheaf_name_prefix + self.node.name)
        self.sheaves[new_sheaf.uid] = new_sheaf

        self.gate_function(input_activation, new_sheaf.uid)


class SlotProxy(object):
    def __init__(self, type, node):

        self.type = type
        self.node = node

    @property
    def activation(self):
        return self.get_activation("default")

    @property
    def incoming(self):
        return self.node.get_slot_links(self.type)

    def get_activation(self, sheaf="default"):
        return self.node.get_slot_sheaf(self.type, sheaf).activation

    @property
    def sheaves(self):
        return self.node.get_slot_sheaves(self.type)

    @sheaves.setter
    def sheaves(self,newValue):
        self.error

    def initialize_sheaves(self):
        self.node.initialize_slot_sheaves(self.type)

    @property
    def current_step(self):
        self.error

    @current_step.setter
    def current_step(self, data):
        self.error


class Slot(object):
    """The entrance of activation into a node. Nodes may have many slots, in which links terminate.

    Attributes:
        type: a string that determines the type of the slot
        node: the parent node of the slot
        activation: a numerical value which is the sum of all incoming activations
        current_step: the simulation step when the slot last received activation
        incoming: a dictionary of incoming links together with the respective activation received by them
    """

    @property
    def current_step(self):
        self._current_step

    @current_step.setter
    def current_step(self, data):
        self._current_step = data

    def __init__(self, nodenet, type, node):
        """create a slot.

        Parameters:
            type: a string that refers to the slot type
            node: the parent node
        """
        self.type = type
        self.node = node
        self.incoming = {}
        self._current_step = -1
        self.sheaves = {"default": SheafElement()}

    @property
    def activation(self):
        return self.get_activation("default")

    def get_activation(self, sheaf="default"):
        if len(self.incoming) == 0:
            return 0
        if sheaf not in self.sheaves:
            return 0
        return self.sheaves[sheaf].activation


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
        "gate_defaults": {
            "gen": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": False
            },
            "por": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": False
            },
            "ret": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": False
            },
            "sub": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": True
            },
            "sur": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": False
            },
            "cat": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": True
            },
            "exp": {
                "minimum": -100,
                "maximum": 100,
                "threshold": -100,
                "spreadsheaves": False
            }
        },
        'symbol': 'πp',
        'shape': 'Rectangle'
    },
    "Activator": {
        "name": "Activator",
        "slottypes": ["gen"],
        "parameters": ["type"],
        "parameter_values": {"type": ["gen", "por", "ret", "sub", "sur", "cat", "exp", "sym", "ref"]},
        "nodefunction_name": "activator"
    }
}


class Nodetype(object):
    """Every node has a type, which is defined by its slot types, gate types, its node function and a list of
    node parameteres."""

    GATE_DEFAULTS = {
        "minimum": -1,
        "maximum": 1,
        "certainty": 1,
        "amplification": 1,
        "threshold": 0,
        "decay": 0,
        "theta": 0,
        "rho": 0,
        "spreadsheaves": False
    }

    @property
    def name(self):
        return self.data["name"]

    @name.setter
    def name(self, identifier):
        self.data["name"] = identifier

    @property
    def slottypes(self):
        return self.data.get("slottypes")

    @slottypes.setter
    def slottypes(self, list):
        self.data["slottypes"] = list

    @property
    def gatetypes(self):
        return self.data.get("gatetypes")

    @gatetypes.setter
    def gatetypes(self, list):
        self.data["gatetypes"] = list

    @property
    def parameters(self):
        return self.data.get("parameters", [])

    @parameters.setter
    def parameters(self, list):
        self.data["parameters"] = list
        self.nodefunction = self.data.get("nodefunction")  # update nodefunction

    @property
    def states(self):
        return self.data.get("states", [])

    @states.setter
    def states(self, list):
        self.data["states"] = list

    @property
    def nodefunction_definition(self):
        return self.data.get("nodefunction_definition")

    @nodefunction_definition.setter
    def nodefunction_definition(self, string):
        self.data["nodefunction_definition"] = string
        args = ','.join(self.parameters).strip(',')
        try:
            self.nodefunction = micropsi_core.tools.create_function(string,
                parameters="nodenet, node, " + args)
        except SyntaxError as err:
            warnings.warn("Syntax error while compiling node function: %s", str(err))
            raise err
            # self.nodefunction = micropsi_core.tools.create_function("""node.activation = 'Syntax error'""",
            #     parameters="nodenet, node, " + args)

    @property
    def nodefunction_name(self):
        return self.data.get("nodefunction_name")

    @nodefunction_name.setter
    def nodefunction_name(self, name):
        self.data["nodefunction_name"] = name
        try:
            from micropsi_core.nodenet import nodefunctions
            if hasattr(nodefunctions, name):
                self.nodefunction = getattr(nodefunctions, name)
            else:
                import nodefunctions as custom_nodefunctions
                self.nodefunction = getattr(custom_nodefunctions, name)

        except (ImportError, AttributeError) as err:
            warnings.warn("Import error while importing node function: nodefunctions.%s %s" % (name, err))
            raise err
            # self.nodefunction = micropsi_core.tools.create_function("""node.activation = 'Syntax error'""",
            #     parameters="nodenet, node")

    def reload_nodefunction(self):
        from micropsi_core.nodenet import nodefunctions
        if self.nodefunction_name and not self.nodefunction_definition and not hasattr(nodefunctions, self.nodefunction_name):
            import nodefunctions as custom_nodefunctions
            from imp import reload
            reload(custom_nodefunctions)
            self.nodefunction = getattr(custom_nodefunctions, self.nodefunction_name)

    def __init__(self, name, nodenet, slottypes=None, gatetypes=None, states=None, parameters=None,
                 nodefunction_definition=None, nodefunction_name=None, parameter_values=None, gate_defaults=None,
                 symbol=None, shape=None):
        """Initializes or creates a nodetype.

        Arguments:
            name: a unique identifier for this nodetype
            nodenet: the nodenet that this nodetype is part of

        If a nodetype with the same name is already defined in the nodenet, it is overwritten. Parameters that
        are not given here will be taken from the original definition. Thus, you may use this initializer to
        set up the nodetypes after loading new nodenet state (by using it without parameters).

        Within the nodenet, the nodenet state dict stores the whole nodenet definition. The part that defines
        nodetypes is structured as follows:

            { "slots": list of slot types or None,
              "gates": list of gate types or None,
              "parameters": string of parameters to store values in or read values from
              "nodefunction": <a string that stores a sequence of python statements, and gets the node and the
                    nodenet as arguments>
            }
        """
        self.data = {'name': name}

        self.states = self.data.get('states', {}) if states is None else states
        self.slottypes = self.data.get("slottypes", ["gen"]) if slottypes is None else slottypes
        self.gatetypes = self.data.get("gatetypes", ["gen"]) if gatetypes is None else gatetypes

        self.gate_defaults = {}
        for g in self.gatetypes:
            self.gate_defaults[g] = Nodetype.GATE_DEFAULTS.copy()

        gate_defaults = self.data.get("gate_defaults") if gate_defaults is None else gate_defaults
        if gate_defaults is not None:
            for g in gate_defaults:
                for key in gate_defaults[g]:
                    if g not in self.gate_defaults:
                        raise Exception("Invalid gate default value for nodetype %s: Gate %s not found" % (name, g))
                    self.gate_defaults[g][key] = gate_defaults[g][key]

        self.parameters = self.data.get("parameters", []) if parameters is None else parameters
        self.parameter_values = self.data.get("parameter_values", []) if parameter_values is None else parameter_values

        if nodefunction_definition:
            self.nodefunction_definition = nodefunction_definition
        elif nodefunction_name:
            self.nodefunction_name = nodefunction_name
        else:
            self.nodefunction = None
