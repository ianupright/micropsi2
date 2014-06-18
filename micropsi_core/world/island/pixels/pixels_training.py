__author__ = 'rvuine'

import logging
import random
from micropsi_core.world.island import island
from micropsi_core.world.island.structured_objects.objects import *
from micropsi_core.world.island.structured_objects.scene import Scene
from micropsi_core.world.worldadapter import WorldAdapter


class PixelsTraining(WorldAdapter):
    """A world adapter exposing pixel training patterns to the agent"""

    datasources = {}
    datatargets = {}

    def __init__(self, world, uid=None, **data):
        super(PixelsTraining, self).__init__(world, uid, **data)

        for x in range(-5, 5):
            for y in range(-5,5):
                datasourcename = "pxl_"+str(x)+"_"+str(y)
                self.datasources[datasourcename] = 0

    def update(self):
        """called on every world simulation step to advance the life of the agent"""

        # we don't move, for now
        self.position = self.world.get_movement_result(self.position, (0, 0))

