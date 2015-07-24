# -*- coding: utf-8 -*-

"""
Netentity definition
"""

import micropsi_core.tools

import libstrongcore_python
from libstrongcore_python import *
from strongcore_python.MicroPsi import *

__author__ = 'joscha'
__date__ = '09.05.12'


class NetEntity(MicroPsiNetEntity):
    """The basic building blocks of node nets.

    Attributes:
        uid: the unique identifier of the net entity
        index: an attempt at creating an ordering criterion for net entities
        name: a human readable name (optional)
        position: a pair of coordinates on the screen
        nodenet: the node net in which the entity resides
        parent_nodespace: the node space this entity is contained in
    """

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, position):
        self.__position = position


    @property
    def parent_nodespace(self):
        return self._parent_nodespace

    @property
    def _parent_nodespace(self):
        node_space = self.getFacetStringValue(MicroPsi.Attr_parent_nodespace)
        if (node_space==""):
            return None
        return node_space

    @_parent_nodespace.setter
    def _parent_nodespace(self,newParent):
        if newParent is None:
            return
        self.setFacetStringValue(MicroPsi.Attr_parent_nodespace, newParent)

    @parent_nodespace.setter
    def parent_nodespace(self, uid):
        if uid:
            nodespace = self.nodenet.get_nodespace(uid)
            if not nodespace.is_entity_known_as(self.entitytype, self.uid):
                nodespace._register_entity(self)
                # tell my old parent that I move out
                if self._parent_nodespace is not None:
                    old_parent = self.nodenet.get_nodespace(self._parent_nodespace)
                    if old_parent and old_parent.uid != uid and old_parent.is_entity_known_as(self.entitytype, self.uid):
                        old_parent._unregister_entity(self.entitytype, self.uid)
            self._parent_nodespace = uid

    def init(self, nodenet, parent_nodespace, position, name="", entitytype="abstract_entities",
                 uid=None, index=None):

        self.__parent_nodespace = None

        self.uid = uid or micropsi_core.tools.generate_uid()
        self.nodenet = nodenet
        self.index = index or len(nodenet.get_node_uids()) + len(nodenet.get_nodespace_uids())
        self.entitytype = entitytype
        self.name = name
        self.position = position
        if parent_nodespace:
            self.parent_nodespace = parent_nodespace
        else:
            self.parent_nodespace = None

    @classmethod
    def new(cls,*args, **kwargs):
        entity = cls.create( args[0].container )
        entity.__class__ = cls
        entity.init(*args,**kwargs)
        return entity

    @property
    def name(self):
        return self.getFacetStringValue( MicroPsi.Attr_name )

    @name.setter
    def name(self,string):
        self.setFacetStringValue( MicroPsi.Attr_name, string )

    @property
    def uid(self):
        return self.getFacetStringValue( MicroPsi.Attr_uid )

    @uid.setter
    def uid(self,string):
        self.setFacetStringValue( MicroPsi.Attr_uid, string )

    @property
    def nodenet_uid(self):
        return self.getFacetStringValue( MicroPsi.Attr_nodenet_uid )

    @nodenet_uid.setter
    def nodenet_uid(self,string):
        self.setFacetStringValue( MicroPsi.Attr_nodenet_uid, string )

    @property
    def nodenet(self):
        return micropsi_core.runtime.get_nodenet(self.nodenet_uid)

    @nodenet.setter
    def nodenet(self,nodenet):
        self.nodenet_uid = nodenet.uid

    @property
    def entitytype(self):
        return self.getFacetStringValue( MicroPsi.Attr_entitytype )

    @entitytype.setter
    def entitytype(self,string):
        self.setFacetStringValue( MicroPsi.Attr_entitytype, string )

    @property
    def index(self):
        return self.getFacetInt64Value( MicroPsi.Attr_index )

    @index.setter
    def index(self,index):
        self.setFacetInt64Value( MicroPsi.Attr_index, index )
