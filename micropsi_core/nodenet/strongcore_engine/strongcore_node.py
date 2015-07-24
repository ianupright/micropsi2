# -*- coding: utf-8 -*-

"""
Node definition

Gate definition
Slot definition
Nodetype definition

default Nodetypes

"""

import logging
import copy

import libstrongcore_python
from libstrongcore_python import *
from strongcore_python.MicroPsi import *

from micropsi_core.nodenet.node import Node, Gate, Nodetype, Slot
from .strongcore_link import StrongCoreLink
from micropsi_core.nodenet.strongcore_engine.strongcore_netentity import NetEntity
import micropsi_core.nodenet.gatefunctions as gatefunctions

__author__ = 'joscha'
__date__ = '09.05.12'


emptySheafElement = dict(uid="default", name="default", activation=0)

class StrongCorePythonNode(object):
    pass


class StrongCoreNode(MicroPsiNode, NetEntity, Node):
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

    def loaded_init(self):
        self._python_node = self.nodenet.python_nodes[self.uid]

    @property
    def python_node(self):
        return self._python_node

    @property
    def activation(self):
        return self.sheaves['default']['activation']

    @property
    def activations(self):
        return dict((k, v['activation']) for k, v in self.sheaves.items())

    @activation.setter
    def activation(self, activation):
        self.set_sheaf_activation(activation)

    def set_sheaf_activation(self, activation, sheaf="default"):
        # print("activation: " + str(activation))
        sheaves_to_calculate = self.get_sheaves_to_calculate()
        if sheaf not in sheaves_to_calculate:
            raise "Sheaf " + sheaf + " can not be set as it hasn't been propagated to any slot"

        if activation is None:
            activation = 0

        self.sheaves[sheaf]['activation'] = float(activation)
        if len(self.nodetype.gatetypes):
            self.set_gate_activation(self.nodetype.gatetypes[0], activation, sheaf)

    def set_slot_sheaves(self, linktype, slotSheaves):
        self.python_node._slot_sheaves[linktype] = slotSheaves

    def get_slot_sheaves(self, linktype):
        slotSheaves = self.python_node._slot_sheaves.get(linktype,None)
        if slotSheaves is None:
            slotSheaves = {}
            self.python_node._slot_sheaves[linktype] = slotSheaves
        return slotSheaves

    def get_gate_sheaves(self, linktype):
        gateSheaves = self.python_node._gate_sheaves.get(linktype,None)
        if gateSheaves is None:
            gateSheaves = {}
            self.python_node._gate_sheaves[linktype] = gateSheaves
        return gateSheaves

    def set_gate_sheaves(self, linktype, gateSheaves):
        self.python_node._gate_sheaves[linktype] = gateSheaves

    def get_parameters_for_gate(self, linktype):
        gateParameters = self.python_node._gate_parameters.get(linktype,None)
        if gateParameters is None:
            gateParameters = {}
            self.python_node._gate_parameters[linktype] = gateParameters
        return gateParameters

    @property
    def type(self):
        return self.getFacetStringValue( MicroPsi.Attr_type )

    @type.setter
    def type(self,string):
        self.setFacetStringValue( MicroPsi.Attr_type, string )

    @property
    def nodetype(self):
        nodetype = self.nodenet.get_nodetype(self.type)
        if nodetype is None:
            return self.nodenet.get_nodetype("Comment")
        return nodetype

    def init(self, nodenet, parent_nodespace, position, state=None, activation=0,
                 name="", type="Concept", uid=None, index=None, parameters=None, gate_parameters=None, gate_activations=None, gate_functions=None, **_):
        if not gate_parameters:
            gate_parameters = {}

        if nodenet.is_node(uid):
            raise KeyError("Node with uid %s already exists" % uid)

        self.type = type

        #Node.__init__(self, type, nodenet.get_nodetype(type))

        NetEntity.init(self, nodenet, parent_nodespace, position,
            name=name, entitytype="nodes", uid=uid, index=index)

        self._python_node = StrongCorePythonNode()

        self.nodenet.python_nodes[self.uid] = self._python_node

        self.python_node.__non_default_gate_parameters = {}

        self.python_node.__state = {}

        self.python_node._slot_sheaves = {}
        self.python_node._gate_sheaves = {}
        self.python_node._gate_parameters = {}

        self.python_node.__gatefunctions = gate_functions or {}
        self.python_node.__parameters = dict((key, self.nodetype.parameter_defaults.get(key)) for key in self.nodetype.parameters)

        if parameters is not None:
            for key in parameters:
                if parameters[key] is not None:
                    self.set_parameter(key, parameters[key])

        for gate_name in gate_parameters:
            for key in gate_parameters[gate_name]:
                if gate_parameters[gate_name][key] != self.nodetype.gate_defaults.get(key, None):
                    if gate_name not in self.python_node.__non_default_gate_parameters:
                        self.python_node.__non_default_gate_parameters[gate_name] = {}
                    self.python_node.__non_default_gate_parameters[gate_name][key] = gate_parameters[gate_name][key]

        gate_parameters = copy.deepcopy(self.nodetype.gate_defaults)
        for gate_name in gate_parameters:
            if gate_name in self.python_node.__non_default_gate_parameters:
                gate_parameters[gate_name].update(self.python_node.__non_default_gate_parameters[gate_name])

        gate_parameters_for_validation = copy.deepcopy(gate_parameters)
        for gate_name in gate_parameters_for_validation:
            for key in gate_parameters_for_validation[gate_name]:
                if key in self.nodetype.gate_defaults:
                    try:
                        gate_parameters[gate_name][key] = float(gate_parameters[gate_name][key])
                    except:
                        logging.getLogger('nodenet').warn('Invalid gate parameter value for gate %s, param %s, node %s' % (gate_name, key, self.uid))
                        gate_parameters[gate_name][key] = self.nodetype.gate_defaults[gate_name].get(key, 0)
                else:
                    gate_parameters[gate_name][key] = float(gate_parameters[gate_name][key])

        self.python_node._gate_parameters = gate_parameters.copy()

        for gate in self.nodetype.gatetypes:
            if gate not in self.python_node.__gatefunctions:
                self.python_node.__gatefunctions[gate] = gatefunctions.identity
            else:
                self.python_node.__gatefunctions[gate] = getattr(gatefunctions, self.python_node.__gatefunctions[gate])
            if gate_activations is None or gate not in gate_activations:
                sheaves_to_use = None
            else:
                sheaves_to_use = gate_activations[gate]

            if sheaves_to_use is None:
                self.python_node._gate_sheaves[gate] = {"default": emptySheafElement.copy()}
            else:
                self.python_node._gate_sheaves[gate] = copy.deepcopy(sheaves_to_use)

            # self.__gates[gate] = DictGate(gate, self, sheaves=sheaves_to_use, parameters=gate_parameters.get(gate))

        for slot in self.nodetype.slottypes:
            self.python_node._slot_sheaves[slot] = {"default": emptySheafElement.copy()}
            # self.__slots[slot] = DictSlot(slot, self)

        if state:
            self.python_node.__state = state
        nodenet._register_node(self)
        self.sheaves = {"default": emptySheafElement.copy()}
        self.activation = activation

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
            node_activation_to_carry_over = {}
            for id in self.sheaves:
                if id in sheaves_to_calculate:
                    node_activation_to_carry_over[id] = self.sheaves[id]

            # clear activation states
            for gatename in self.get_gate_types():
                gate = self.get_gate(gatename)
                gate.sheaves = {}
            self.sheaves = {}

            # calculate activation states for all open sheaves
            for sheaf_id in sheaves_to_calculate:
                # print("node: " + self.name + " sheaf_id: " + sheaf_id)
                # prepare sheaves
                for gatename in self.get_gate_types():
                    gate = self.get_gate(gatename)
                    gate.sheaves[sheaf_id] = sheaves_to_calculate[sheaf_id].copy()
                if sheaf_id in node_activation_to_carry_over:
                    self.sheaves[sheaf_id] = node_activation_to_carry_over[sheaf_id].copy()
                    self.set_sheaf_activation(node_activation_to_carry_over[sheaf_id]['activation'], sheaf_id)
                else:
                    self.sheaves[sheaf_id] = sheaves_to_calculate[sheaf_id].copy()
                    self.set_sheaf_activation(0, sheaf_id)

            # and actually calculate new values for them
            for sheaf_id in sheaves_to_calculate:

                try:
                    self.nodetype.nodefunction(netapi=self.nodenet.netapi, node=self, sheaf=sheaf_id, **self.parameters)
                except Exception:
                    self.nodenet.is_active = False
                    self.activation = -1
                    raise
        else:
            # default node function (only using the "default" sheaf)
            if len(self.get_slot_types()):
                self.activation = sum([self.get_slot(slot).activation for slot in self.get_slot_types()])
                if len(self.get_gate_types()):
                    for gatetype in self.get_gate_types():
                        self.get_gate(gatetype).gate_function(self.activation)

    def get_gate(self, gatename):
        return StrongCoreGate( gatename, self )
        #return self.gates.get(gatename)

    def get_slot(self, slotname):
        return StrongCoreSlot( slotname, self )
        #return self.slots.get(slotname)

    @property
    def gates(self):
        gates = []
        for slot in self.nodetype.gatetypes:
            gates.append( self.get_gate(slot) )
        return gates

    @property
    def slots(self):
        slots = []
        for slot in self.nodetype.slottypes:
            slots.append( self.get_slot(slot) )
        return slots

    def get_slot_sheaf(self, linktype, sheaf):
        sloatSheaves = self.get_slot_sheaves(linktype)
        sheafElement = sloatSheaves.get(sheaf,None)
        if sheafElement is None:
            sheafElement = {}
            sloatSheaves[sheaf] = sheafElement
        return sheafElement

    def get_gate_sheaf(self, linktype, sheaf):
        gateSheaves = self.get_gate_sheaves(linktype)
        sheafElement = gateSheaves.get(sheaf,None)
        if sheafElement is None:
            sheafElement = {}
            gateSheaves[sheaf] = sheafElement
        return sheafElement

    def set_gate_activation(self, gatetype, activation, sheaf="default"):
        """ sets the activation of the given gate"""
        activation = float(activation)
        if gatetype in self.get_gate_types():
            sheafElement = self.get_gate_sheaf(gatetype,sheaf)
            sheafElement['activation'] = activation

    def get_sheaves_to_calculate(self):
        sheaves_to_calculate = {}
        for slotname in self.get_slot_types():
            for uid in self.get_slot(slotname).sheaves:
                sheaves_to_calculate[uid] = self.get_slot(slotname).sheaves[uid].copy()
                sheaves_to_calculate[uid]['activation'] = 0
        if 'default' not in sheaves_to_calculate:
            sheaves_to_calculate['default'] = emptySheafElement.copy()
        return sheaves_to_calculate

    def get_gate_parameters(self):
        """Looks into the gates and returns gate parameters if these are defined"""
        gate_parameters = {}
        for gatetype in self.get_gate_types():
            if self.get_gate(gatetype).parameters:
                gate_parameters[gatetype] = self.get_gate(gatetype).parameters
        if len(gate_parameters):
            return gate_parameters
        else:
            return None

    def clone_non_default_gate_parameters(self, gate_type=None):
        if gate_type is None:
            return self.python_node.__non_default_gate_parameters.copy()
        if gate_type not in self.python_node.__non_default_gate_parameters:
            return None
        return {
            gate_type: self.python_node.__non_default_gate_parameters[gate_type].copy()
        }

    def set_gate_parameter(self, gate_type, parameter, value):
        if self.python_node.__non_default_gate_parameters is None:
            self.python_node.__non_default_gate_parameters = {}
        if parameter in self.nodetype.gate_defaults[gate_type]:
            if value is None:
                value = self.nodetype.gate_defaults[gate_type][parameter]
            else:
                value = float(value)
            if value != self.nodetype.gate_defaults[gate_type][parameter]:
                if gate_type not in self.python_node.__non_default_gate_parameters:
                    self.python_node.__non_default_gate_parameters[gate_type] = {}
                self.python_node.__non_default_gate_parameters[gate_type][parameter] = value
            elif parameter in self.python_node.__non_default_gate_parameters.get(gate_type, {}):
                del self.python_node.__non_default_gate_parameters[gate_type][parameter]
        self.get_gate(gate_type).parameters[parameter] = value

    def get_gatefunction(self, gate_type):
        if self.get_gate(gate_type):
            return self.python_node.__gatefunctions[gate_type]
        raise KeyError("Wrong Gatetype")

    def get_gatefunction_name(self, gate_type):
        if self.get_gate(gate_type):
            return self.python_node.__gatefunctions[gate_type].__name__
        raise KeyError("Wrong Gatetype")

    def set_gatefunction_name(self, gate_type, gatefunction):
        if self.get_gate(gate_type):
            if gatefunction is None:
                self.python_node.__gatefunctions[gate_type] = gatefunctions.identity
            elif hasattr(gatefunctions, gatefunction):
                self.python_node.__gatefunctions[gate_type] = getattr(gatefunctions, gatefunction)
            else:
                raise NameError("Unknown Gatefunction")
        else:
            raise KeyError("Wrong Gatetype")

    def get_gatefunction_names(self):
        ret = {}
        for key in self.python_node.__gatefunctions:
            ret[key] = self.python_node.__gatefunctions[key].__name__
        return ret

    def reset_slots(self):
        for slot in self.nodetype.slottypes:
            self.python_node._slot_sheaves[slot] = {"default": emptySheafElement.copy()}

    @property
    def parameters(self):
        return self.python_node.__parameters

    def get_parameter(self, parameter):
        if parameter in self.python_node.__parameters:
            return self.python_node.__parameters[parameter]
        else:
            return None

    def clear_parameter(self, parameter):
        if parameter in self.python_node.__parameters:
            if parameter not in self.nodetype.parameters:
                del self.python_node.__parameters[parameter]
            else:
                self.python_node.__parameters[parameter] = None

    def set_parameter(self, parameter, value):
        if (value == '' or value is None):
            if parameter in self.nodetype.parameter_defaults:
                value = self.nodetype.parameter_defaults[parameter]
            else:
                value = None
        self.python_node.__parameters[parameter] = value

    def clone_parameters(self):
        return self.python_node.__parameters.copy()

    def clone_sheaves(self):
        return self.sheaves.copy()

    def get_state(self, state_element):
        if state_element in self.python_node.__state:
            return self.python_node.__state[state_element]
        else:
            return None

    def set_state(self, state_element, value):
        self.python_node.__state[state_element] = value

    def clone_state(self):
        return self.python_node.__state.copy()

    def link(self, gate_name, target_node_uid, slot_name, weight=1, certainty=1):
        """Ensures a link exists with the given parameters and returns it
           Only one link between a node/gate and a node/slot can exist, its parameters will be updated with the
           given parameters if a link existed prior to the call of this method
           Will return None if no such link can be created.
        """

        if not self.nodenet.is_node(target_node_uid):
            return None

        target = self.nodenet.get_node(target_node_uid)

        if slot_name not in target.get_slot_types():
            return None

        gate = self.get_gate(gate_name)
        if gate is None:
            return None
        link = None

        self.set_link_weight( gate_name, target, slot_name, weight )
        self.set_link_certainty( gate_name, target, slot_name, certainty )
        target.add_slot_link( slot_name, self, gate_name )

        #for candidate in gate.get_links():
        #    if candidate.target_node.uid == target.uid and candidate.target_slot == slot_name:
        #        link = candidate
        #        break
        #if link is None:
        #    link = StrongCoreLink(self, gate_name, target, slot_name)

        #link.set_weight(weight, certainty)

        return link

    def unlink_completely(self):
        """Deletes all links originating from this node or ending at this node"""
        links_to_delete = set()
        for gate_name_candidate in self.get_gate_types():
            for link_candidate in self.get_gate(gate_name_candidate).get_links():
                links_to_delete.add(link_candidate)
        for slot_name_candidate in self.get_slot_types():
            for link_candidate in self.get_slot(slot_name_candidate).get_links():
                links_to_delete.add(link_candidate)
        for link in links_to_delete:
            link.remove()

    def unlink(self, gate_name=None, target_node_uid=None, slot_name=None):
        links_to_delete = set()
        for gate_name_candidate in self.get_gate_types():
            if gate_name is None or gate_name == gate_name_candidate:
                for link_candidate in self.get_gate(gate_name_candidate).get_links():
                    if target_node_uid is None or target_node_uid == link_candidate.target_node.uid:
                        if slot_name is None or slot_name == link_candidate.target_slot.type:
                            links_to_delete.add(link_candidate)
        for link in links_to_delete:
            link.remove()

    def remove_gate_link_data(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        self.fromFacetRemove(rel, target_node)
        rel = self.nodenet.get_or_create_certainty_relationship(gate_type,slot_type)
        self.fromFacetRemove(rel, target_node)

    def get_link_weight(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        return rel.forObjectAt( self, target_node )

    def set_link_weight(self,gate_type,target_node,slot_type,weight):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        self.toFacetAddDouble( rel, target_node, weight )

    def get_link_certainty(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_certainty_relationship(gate_type,slot_type)
        return rel.forObjectAt( self, target_node )

    def set_link_certainty(self,gate_type,target_node,slot_type,certainty):
        rel = self.nodenet.get_or_create_certainty_relationship(gate_type,slot_type)
        self.toFacetAddDouble( rel, target_node, certainty )

    def get_slot_links(self,slot_type):
        links = []
        slot_type_prototype = self.nodenet.get_or_create_linktype_prototype(slot_type)
        slotRelationships = self.getSlotRelationshipsMatching(slot_type_prototype)
        for slot_rel in slotRelationships:
            slot_rel = Facet.safeCast(slot_rel)
            gate_rel = slot_rel.getAny(Core.Rel_Inverse_Relationship)
            gate_type = gate_rel.prototype().getLabel()
            slot_links = self.get(slot_rel)
            for node in slot_links:
                node = StrongCoreNode.safeCast(node)
                node.__class__ = StrongCoreNode
                node.loaded_init()
                weight = node.get_link_weight( gate_type, self, slot_type )
                certainty =  node.get_link_certainty( gate_type, self, slot_type )
                links.append( StrongCoreLink( node, gate_type, self, slot_type, weight, certainty ))
        return links

    def get_slot_links_with_gate(self,slot_type,gate_type):
        links = []
        slot_type_prototype = self.nodenet.get_or_create_linktype_prototype(slot_type)
        slotRelationships = self.getSlotsMatching(slot_type_prototype)
        for slot_rel in slotRelationships:
            slot_type = slot_rel.prototype().getLabel()
            slot_links = self.get(slot_rel)
            for node in slot_links:
                weight = node.get_link_weight( gate_type, self, slot_type )
                certainty =  node.get_link_certainty( gate_type, self, slot_type )
                casted_node = MicroPsiNode.safeCast(node)
                casted_node.__class__ = StrongCoreNode
                casted_node.loaded_init()
                links.append( StrongCoreLink( casted_node, gate_type, self, slot_type, weight, certainty ))
        return links

    def get_gate_links(self, gate_type):
        links = []
        gate_type_prototype = self.nodenet.get_or_create_linktype_prototype(gate_type)
        gateRelationships = self.getGateRelationshipsMatching(gate_type_prototype)
        for gate_rel in gateRelationships:
            gate_rel = Facet.safeCast(gate_rel)
            slot_rel = gate_rel.getAny(Core.Rel_Inverse_Relationship)
            slot_type = slot_rel.prototype().getLabel()
            gate_links = self.get(gate_rel)
            for node in gate_links:
                weight = self.get_link_weight(gate_type, node, slot_type)
                certainty =  self.get_link_certainty(gate_type, node, slot_type)
                casted_node = MicroPsiNode.safeCast(node)
                casted_node.__class__ = StrongCoreNode
                casted_node.loaded_init()
                links.append(StrongCoreLink(self, gate_type, casted_node, slot_type, weight, certainty))
        return links


    def add_slot_link(self,slot_type,source_node,gate_type):
        gateRel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        slotRel = Facet.safeCast( gateRel.getAny(Core.Rel_Inverse_Relationship) )
        self.toFacetAdd( slotRel, source_node )

    def remove_slot_link(self,slot_type,source_node,gate_type):
        gateRel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        slotRel = gateRel.getAny( Core.Rel_Inverse_Relationship )
        slotRel = Facet.safeCast( slotRel )
        self.fromFacetRemove( slotRel, source_node )

    def unlink_all_gates(self):
        gateRelationships = self.getGateRelationships()
        for gate_rel in gateRelationships:
            gate_rel = Facet.safeCast(gate_rel)
            gate_type = gate_rel.prototype().getLabel()
            slot_rel = gate_rel.getAny(Core.Rel_Inverse_Relationship)
            slot_type = slot_rel.prototype().getLabel()
            target_nodes = self.get(gate_rel)
            for target_node in target_nodes:
                target_node = MicroPsiNode.safeCast(target_node)
                target_node.remove_slot_link(slot_type,self,gate_type)
            self.clearFacet(gate_rel)
            size = self.get(gate_rel).size()
            print(size)

    def unlink_all_slots(self):
        slotRelationships = self.getSlotRelationships()
        for slot_rel in slotRelationships:
            slot_rel = Facet.safeCast(slot_rel)
            slot_type = slot_rel.prototype().getLabel()
            gate_rel = slot_rel.getAny(Core.Rel_Inverse_Relationship)
            gate_type = gate_rel.prototype().getLabel()
            source_nodes = self.get(slot_rel)
            for source_node in source_nodes:
                source_node = MicroPsiNode.safeCast(source_node)
                source_node.remove_gate_link_data(gate_type,self,slot_type)
            self.clearFacet(slot_rel)
            size = self.get(slot_rel).size()
            print(size)

    def unlink_using_node(self,gate_type,target_node,slot_type):
        self.remove_gate_link_data(gate_type,target_node,slot_type)
        target_node.remove_slot_link(slot_type,self,gate_type)


class StrongCoreGate(Gate):
    """The activation outlet of a node. Nodes may have many gates, from which links originate.

    Attributes:
        type: a string that determines the type of the gate
        node: the parent node of the gate
        sheaves: a dict of sheaves this gate initially has to support
        parameters: a dictionary of values used by the gate function
    """

    @property
    def type(self):
        return self.__type

    @property
    def node(self):
        return self.__node

    @property
    def empty(self):
        return len(self.__outgoing) == 0

    @property
    def activation(self):
        return self.sheaves['default']['activation']

    @property
    def activations(self):
        return dict((k, v['activation']) for k, v in self.sheaves.items())

    @property
    def sheaves(self):
        return self.node.get_gate_sheaves(self.type)

    @sheaves.setter
    def sheaves(self,sheaves):
        self.node.set_gate_sheaves(self.type,sheaves)

    @property
    def parameters(self):
        return self.node.get_parameters_for_gate(self.type)

    def __init__(self, type, node):
        self.__type = type
        self.__node = node

    def get_links(self):
        return self.__node.get_gate_links(self.__type)

    @property
    def links(self):
        return self.get_links()

    def get_parameter(self, parameter_name):
        return self.parameters[parameter_name]

    def clone_sheaves(self):
        return self.sheaves.copy()

    def gate_function(self, input_activation, sheaf="default"):
        """This function sets the activation of the gate.

        The gate function should be called by the node function, and can be replaced by different functions
        if necessary. This default gives a linear function (input * amplification), cut off below a threshold.
        You might want to replace it with a radial basis function, for instance.
        """
        if input_activation is None:
            input_activation = 0

        #print("node:" + self.node.uid + " gate function")

        #if (self.type=="sub" and self.node.name==""):
        #    print("here2")

        # check if the current node space has an activator that would prevent the activity of this gate
        nodespace = self.node.nodenet.get_nodespace(self.node.parent_nodespace)
        if nodespace.has_activator(self.type):
            gate_factor = nodespace.get_activator_value(self.type)
        else:
            gate_factor = 1.0
        if gate_factor == 0.0:
            self.sheaves[sheaf]['activation'] = 0
            return 0  # if the gate is closed, we don't need to execute the gate function

        gatefunction = self.__node.get_gatefunction(self.__type)

        if gatefunction:
            activation = gatefunction(input_activation, self.parameters.get('rho', 0), self.parameters.get('theta', 0))
        else:
            activation = input_activation

        if activation * gate_factor < self.parameters['threshold']:
            activation = 0
        else:
            activation = activation * self.parameters["amplification"] * gate_factor

        activation = min(self.parameters["maximum"], max(self.parameters["minimum"], activation))

        self.sheaves[sheaf]['activation'] = activation

        return activation

    def open_sheaf(self, input_activation, sheaf="default"):
        """This function opens a new sheaf and calls the gate function for the newly opened sheaf
        """
        if sheaf is "default":
            sheaf_uid_prefix = "default" + "-"
            sheaf_name_prefix = ""
        else:
            sheaf_uid_prefix = sheaf + "-"
            sheaf_name_prefix = self.sheaves[sheaf]['name'] + "-"

        new_sheaf = dict(uid=sheaf_uid_prefix + self.node.uid, name=sheaf_name_prefix + self.node.name, activation=0)
        self.sheaves[new_sheaf['uid']] = new_sheaf

        self.gate_function(input_activation, new_sheaf['uid'])


class StrongCoreSlot(Slot):
    """The entrance of activation into a node. Nodes may have many slots, in which links terminate.

    Attributes:
        type: a string that determines the type of the slot
        node: the parent node of the slot
        activation: a numerical value which is the sum of all incoming activations
        current_step: the simulation step when the slot last received activation
        incoming: a dictionary of incoming links together with the respective activation received by them
    """

    @property
    def type(self):
        return self.__type

    @property
    def node(self):
        return self.__node

    @property
    def empty(self):
        return len(self.get_links()) == 0

    @property
    def activation(self):
        return self.sheaves['default']['activation']

    @property
    def activations(self):
        return dict((k, v['activation']) for k, v in self.sheaves.items())

    @property
    def sheaves(self):
        return self.node.get_slot_sheaves(self.type)

    @sheaves.setter
    def sheaves(self,sheaves):
        self.node.set_slot_sheaves(self.type,sheaves)

    def __init__(self, type, node):
        self.__type = type
        self.__node = node
        self.__incoming = {}

    def get_activation(self, sheaf="default"):
        if self.empty:
            return 0
        sheaves = self.sheaves
        if sheaf not in sheaves:
            return 0
        return sheaves[sheaf]['activation']

    def get_links(self):
        return self.__node.get_slot_links(self.__type)

    @property
    def links(self):
        return self.get_links()
