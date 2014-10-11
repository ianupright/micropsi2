import libstrongcore_python
from libstrongcore_python import *
from micropsi_core import *

import micropsi_core.nodenet.netentity
from micropsi_core.nodenet.netentity import *
import micropsi_core.nodenet.nodenet
from micropsi_core.nodenet.nodenet import *
from micropsi_core.nodenet.node import *
from strongcore_python.MicroPsi import *
import inspect

swigMethods = { '__swig_destroy__' , '__swig_getmethods__', '__swig_setmethods__' }

def is_bound_method(obj):
    return hasattr(obj, '__self__') and obj.__self__ is not None

def copyAllMethods( fromClass, toClass ):
    attributes = dir(fromClass)
    methods = inspect.getmembers(fromClass)
    for methodTuple in methods:
        if methodTuple[0].startswith('__'):
            if methodTuple[0] in swigMethods:
                setattr( toClass, methodTuple[0], methodTuple[1])
        else:
            if hasattr(methodTuple[1],'__qualname__'):
                methodClassName = methodTuple[1].__qualname__
                methodClassName = methodClassName.rpartition('.')[0]
                if fromClass.__name__ == methodClassName:
                    if (is_bound_method(methodTuple[1])):
                        setattr( toClass, methodTuple[0], classmethod(methodTuple[1].__func__) )
                    else:
                        setattr( toClass, methodTuple[0], methodTuple[1] )
            if hasattr(methodTuple[1],'fget'):
                methodClassName = methodTuple[1].fget.__qualname__
                methodClassName = methodClassName.rpartition('.')[0]
                if fromClass.__name__ == methodClassName:
                    setattr( toClass, methodTuple[0], methodTuple[1] )

_isInitialized = False

set_NetEntity_class(MicroPsiNetEntity)
set_Nodespace_class(MicroPsiNodespace)
set_Node_class(MicroPsiNode)

copyAllMethods( BasicNetEntity, MicroPsiBasicNetEntity )
copyAllMethods( NetEntity, MicroPsiNetEntity )
copyAllMethods( Nodespace, MicroPsiNodespace )
copyAllMethods( Node, MicroPsiNode )


nodenetContainers = {}

class Nodenet_strongcore_changes(object):

    def getContainerName(self):
        containerName = self.filename
        containerName = containerName.rpartition('.json')[0]
        containerName = containerName + ".dat"
        return containerName

    def beforeload(self):
        global _isInitialized
        if not _isInitialized:
            StrongCore.initialize()
            CoreGlobals.loadOrCreateGlobals()
            Core.load()
            MicroPsi.load()
            _isInitialized = True

        containerName = self.getContainerName()
        existingNodenet = nodenetContainers.get( containerName, None)
        if existingNodenet is not None:
            existingNodenet.unload()

        self.container = Container.createContainer( containerName )
        nodenetContainers[containerName]=self

        self._linkTypeToPrototypes = {}
        self._gateRelationships = {}
        self._weightRelationships = {}
        self._certaintyRelationships = {}

    def unload(self):
        self.beforeunload()
        self.container.close()
        del nodenetContainers[self.getContainerName()]

    def get_or_create_linktype_prototype(self,link_type):
        linktype_prototype = self._linkTypeToPrototypes.get(link_type,None)
        if linktype_prototype is None:
            linktype_prototype = MicroPsiGateRelationship_create( self.container )
            linktype_prototype.setLabel( link_type )
            self._linkTypeToPrototypes[link_type] = linktype_prototype
        return linktype_prototype

    def create_gate_relationship(self,gate_type,slot_type):
        gate_type_prototype = self.get_or_create_linktype_prototype(gate_type)
        slot_type_prototype = self.get_or_create_linktype_prototype(slot_type)
        slotMap = self._gateRelationships.get(gate_type,None)
        if slotMap is None:
            slotMap = {}
            self._gateRelationships[gate_type] = slotMap
        gate_relationship = MicroPsiGateRelationship.create( self.container )
        slot_relationship = MicroPsiSlotRelationship.create( self.container )
        gate_relationship.setPrototypeTo( gate_type_prototype )
        gate_relationship.setLabel( "gate relationship for " + gate_type + "_" + slot_type )
        slot_relationship.setPrototypeTo( slot_type_prototype )
        slot_relationship.setLabel( "inverse of gate relationship for " + gate_type + "_" + slot_type )
        gate_relationship.toFacetAdd( Core.Rel_Inverse_Relationship, slot_relationship)
        slot_relationship.toFacetAdd( Core.Rel_Inverse_Relationship, gate_relationship)
        slotMap[slot_type] = gate_relationship
        return gate_relationship

    def get_or_create_gate_relationship(self,gate_type,slot_type):
        slotMap = self._gateRelationships.get(gate_type,None)
        if slotMap is None:
            return self.create_gate_relationship(gate_type,slot_type)
        relationship = slotMap.get(slot_type,None)
        if relationship is None:
            return self.create_gate_relationship(gate_type,slot_type)
        return relationship

    def create_certainty_relationship(self,gate_type,slot_type):
        slotMap = self._certaintyRelationships.get(gate_type,None)
        if slotMap is None:
            slotMap = {}
            self._certaintyRelationships[gate_type] = slotMap
        certainty_relationship = WeightedRelationship.create( self.container )
        certainty_relationship.setLabel( "certainty for " + gate_type + "_" + slot_type )
        slotMap[slot_type] = certainty_relationship
        return certainty_relationship

    def get_or_create_certainty_relationship(self,gate_type,slot_type):
        slotMap = self._certaintyRelationships.get(gate_type,None)
        if slotMap is None:
            return self.create_certainty_relationship(gate_type,slot_type)
        relationship = slotMap.get(slot_type,None)
        if relationship is None:
            return self.create_certainty_relationship(gate_type,slot_type)
        return relationship

class NetEntity_strongcore_changes(object):

    @property
    def _name(self):
        return self.getFacetStringValue( MicroPsi.Attr_name )

    @_name.setter
    def _name(self,string):
        self.setFacetStringValue( MicroPsi.Attr_name, string )

    @property
    def _uid(self):
        return self.getFacetStringValue( MicroPsi.Attr_uid )

    @_uid.setter
    def _uid(self,string):
        self.setFacetStringValue( MicroPsi.Attr_uid, string )

    @property
    def _nodenet_uid(self):
        return self.getFacetStringValue( MicroPsi.Attr_nodenet_uid )

    @_nodenet_uid.setter
    def _nodenet_uid(self,string):
        self.setFacetStringValue( MicroPsi.Attr_nodenet_uid, string )

    @property
    def _entitytype(self):
        return self.getFacetStringValue( MicroPsi.Attr_entitytype )

    @_entitytype.setter
    def _entitytype(self,string):
        self.setFacetStringValue( MicroPsi.Attr_entitytype, string )

    @property
    def _index(self):
        return self.getFacetIntegerValue( MicroPsi.Attr_index )

    @_index.setter
    def _index(self,index):
        self.setFacetIntegerValue( MicroPsi.Attr_index, index )


class Node_strongcore_changes(object):

    def getNodePythonData(self):
        nodenet = self.nodenet
        nodeData = nodenet.nodeData.get(self.getValueOid(), None)
        if nodeData is None:
            nodeData = NodeData()
            nodenet.nodeData[self.getValueOid()] = nodeData
        return nodeData

    @property
    def sheaves(self):
        return self.getNodePythonData().sheaves

    @sheaves.setter
    def sheaves(self,newSheaves):
        self.getNodePythonData().sheaves = newSheaves

    @property
    def _slot_sheaves(self):
        return self.getNodePythonData()._slot_sheaves

    @_slot_sheaves.setter
    def _slot_sheaves(self,newSheaves):
        self.getNodePythonData()._slot_sheaves = newSheaves

    @property
    def _gate_sheaves(self):
        return self.getNodePythonData()._gate_sheaves

    @_gate_sheaves.setter
    def _gate_sheaves(self,newSheaves):
        self.getNodePythonData()._gate_sheaves = newSheaves

    @property
    def _type(self):
        return self.getFacetStringValue( MicroPsi.Attr_type )

    @_type.setter
    def _type(self,string):
        self.setFacetStringValue(MicroPsi.Attr_type, string)
        self._gate_links_to_data = None
        self._slot_links_to_node = None

    @property
    def _parent_nodespace(self):
        return self.getFacetStringValue(MicroPsi.Attr_parent_nodespace)

    @_parent_nodespace.setter
    def _parent_nodespace(self,newParent):
        if newParent is None:
            return
        self.setFacetStringValue(MicroPsi.Attr_parent_nodespace, newParent)

    def get_gate_link_data(self,gate_type,target_node,slot_type):
        self.error

    def get_or_create_gate_link_data(self,gate_type,target_node,slot_type):
        self.error

    def remove_gate_link_data(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        self.fromFacetRemove(rel, target_node)
        rel = self.nodenet.get_or_create_certainty_relationship(gate_type,slot_type)
        self.fromFacetRemove(rel, target_node)

    def get_or_create_slot_links(self,slot_type,gate_type):
        self.error

    def get_link_weight(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        return self.getDoubleForFacetAndObject( rel, target_node )

    def set_link_weight(self,gate_type,target_node,slot_type,weight):
        rel = self.nodenet.get_or_create_gate_relationship(gate_type,slot_type)
        self.toFacetAddDouble( rel, target_node, weight )

    def get_link_certainty(self,gate_type,target_node,slot_type):
        rel = self.nodenet.get_or_create_certainty_relationship(gate_type,slot_type)
        return self.getDoubleForFacetAndObject( rel, target_node )

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
                node = MicroPsiNode.safeCast(node)
                weight = node.get_link_weight( gate_type, self, slot_type )
                certainty =  node.get_link_certainty( gate_type, self, slot_type )
                links.append( LinkProxy( node, gate_type, self, slot_type, weight, certainty ))
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
                links.append( LinkProxy( MicroPsiNode.safeCast(node), gate_type, self, slot_type, weight, certainty ))
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
                links.append(LinkProxy(self, gate_type, MicroPsiNode.safeCast(node), slot_type, weight, certainty))
        return links

    def get_gate_link(self, gate_type, target_node, slot_type):
        self.error

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

copyAllMethods( Nodenet_strongcore_changes, Nodenet )
copyAllMethods( NetEntity_strongcore_changes, MicroPsiNetEntity )
copyAllMethods( Node_strongcore_changes, MicroPsiNode )