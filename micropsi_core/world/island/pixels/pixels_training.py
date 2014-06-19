__author__ = 'rvuine'

import logging
import random
from micropsi_core.world.island import island
from micropsi_core.world.island.structured_objects.objects import *
from micropsi_core.world.island.structured_objects.scene import Scene
from micropsi_core.world.island.pixels import patterngenerator
from micropsi_core.world.worldadapter import WorldAdapter


class PixelsTraining(WorldAdapter):
    """A world adapter exposing pixel training patterns to the agent"""

    datasources = {"is_empty": 1, "is_vertical": 0}
    datatargets = {"new_empty": 1, "new_vertical": 0}

    currentpattern = []

    def __init__(self, world, uid=None, **data):
        super(PixelsTraining, self).__init__(world, uid, **data)

        self.currentpattern = patterngenerator.create_shape(None)
        for x in range(0, len(self.currentpattern)):
            for y in range(0, len(self.currentpattern[0])):
                datasourcename = "pxl_"+str(x)+"_"+str(y)
                self.datasources[datasourcename] = self.currentpattern[x][y]

    def update(self):
        """called on every world simulation step to advance the life of the agent"""

        # we don't move, for now
        #self.position = self.world.get_movement_result(self.position, (0, 0))

        if self.datatargets['new_empty'] > 0:
            self.currentpattern = patterngenerator.create_shape(None)
            for key in self.datasources.keys():
                self.datasources[key] = 0
            self.datasources['is_empty'] = 1

        if self.datatargets['new_vertical'] > 0:
            self.currentpattern = patterngenerator.create_shape("vertical")
            for key in self.datasources.keys():
                self.datasources[key] = 0
            self.datasources['is_vertical'] = 1

        for key in self.datatargets.keys():
            self.datatargets[key] = 0
