# -*- coding: utf-8 -*-

"""
Netentity definition
"""

import micropsi_core.tools
from micropsi_core.tools import NetEntityDataProxy

__author__ = 'joscha'
__date__ = '09.05.12'

class VeryBasicNetEntity(object):
    @classmethod
    def create(cls, container):
        return cls()

class BasicNetEntity(VeryBasicNetEntity):
    @classmethod
    def new(cls,*args, **kwargs):
        entity = cls.create( args[0].container )
        entity.init(*args,**kwargs)
        return entity

    def get_data_properties(self):
        return []

    def get_data_property(self, propertyName):
        value = getattr(self, "_" + propertyName, None)
        return value

    def get_data(self):
        return_data = {}
        for dataKey in self.get_data_properties():
            value = self.get_data_property(dataKey)
            if value is not None:
                return_data[dataKey] = value
        return return_data

    def set_data(self, data):
        for dataKey in data.keys():
            setter = getattr(self, "_" + dataKey, None)
            # if setter is not None:
            #     setter( data[dataKey] )
            # else:
            setattr(self, "_" + dataKey, data[dataKey])

class NetEntity(BasicNetEntity):
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
    def data(self):
        self.error

    @data.setter
    def data(self, data):
        self.error

    def get_data_properties(self):
        return ['uid', 'index', 'name', 'position', 'parent_nodespace' ]

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self,uid):
        self._uid = uid

    @property
    def entitytype(self):
        return self._entitytype

    @entitytype.setter
    def entitytype(self,entitytype):
        self._entitytype = entitytype

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self,index):
        self._index = index

    #define a dummy property for _name, which serves as a test case to ensure get_data and set_data working correctly

    @property
    def _name(self):
        return self.__name

    @_name.setter
    def _name(self, string):
        self.__name= string

    @property
    def name(self):
        return self._name or self._uid

    @name.setter
    def name(self, string):
        self._name = string

    @property
    def nodenet_uid(self):
        return self._nodenet_uid

    @nodenet_uid.setter
    def nodenet_uid(self, id):
        self._nodenet_uid = id

    @property
    def nodenet(self):
        return micropsi_core.runtime.get_nodenet_or_none(self.nodenet_uid)

    @property
    def position(self):
        return self._position or (0, 0)

    @position.setter
    def position(self, pos):
        self._position = pos

    @property
    def parent_nodespace(self):
        return self._parent_nodespace or 0

    def set_parent_nodespace(self, uid, nodenet):
        nodespace = nodenet.nodespaces[uid]
        if self.entitytype not in nodespace.netentities:
            nodespace.netentities[self.entitytype] = []
        if self.uid not in nodespace.netentities[self.entitytype]:
            nodespace.netentities[self.entitytype].append(self.uid)
            #if uid in self.nodenet.state["nodespaces"][uid][self.entitytype]:
            #    self.nodenet.state["nodespaces"][uid][self.entitytype] = self.uid
            # tell my old parent that I move out
            if self._parent_nodespace is not None:
                old_parent = nodenet.nodespaces.get(self._parent_nodespace)
                if old_parent and old_parent.uid != uid and self.uid in old_parent.netentities.get(self.entitytype, []):
                    old_parent.netentities[self.entitytype].remove(self.uid)
        self._parent_nodespace = uid

    def init(self, nodenet, parent_nodespace, position, name="", entitytype="abstract_entities",
                 uid=None, index=None):
        """create a net entity at a certain position and in a given node space"""
        if uid in nodenet.state.get("entitytype", []):
            raise KeyError("Netentity already exists")

        uid = uid or micropsi_core.tools.generate_uid()
        self.nodenet_uid = nodenet.uid
        if not entitytype in nodenet.state:
            nodenet.state[entitytype] = {}
        if not uid in nodenet.state[entitytype]:
            nodenet.state[entitytype][uid] = NetEntityDataProxy(self)
        self.uid = uid
        self.index = index or len(nodenet.state.get("nodes", [])) + len(nodenet.state.get("nodespaces", []))
        self.entitytype = entitytype
        self.name = name
        self.position = position
        self._parent_nodespace = None
        if parent_nodespace:
            self.set_parent_nodespace( parent_nodespace, nodenet )

_NetEntity_class = NetEntity

def NetEntity_class():
    return _NetEntity_class

def set_NetEntity_class(newClass):
    global _NetEntity_class
    _NetEntity_class = newClass
