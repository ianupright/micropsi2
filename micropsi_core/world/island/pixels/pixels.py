__author__ = 'rvuine'

import logging
from micropsi_core.world.island import island
from micropsi_core.world.island.structured_objects.objects import *
from micropsi_core.world.island.structured_objects.scene import Scene
from micropsi_core.world.worldadapter import WorldAdapter


class Pixels(WorldAdapter):
    """A world adapter exposing a pixel fovea to the agent"""

    fovea_x = 0
    fovea_y = 0

    datasources = {'major-newscene': 0}
    datatargets = {'fov_x': 0, 'fov_y': 0, 'fov_reset': 0}

    currentobject = None

    def __init__(self, world, uid=None, **data):
        super(Pixels, self).__init__(world, uid, **data)

        for x in range(-5, 5):
            for y in range(-5,5):
                datasourcename = "pxl_"+str(x)+"_"+str(y)
                self.datasources[datasourcename] = 0

    def initialize_worldobject(self, data):
        if not "position" in data:
            self.position = self.world.groundmap['start_position']

    def get_datasource(self, key):
        """
            allows the agent to read a value from a datasource.
            overrides default to make sure newscene signals are picked up by the node net
        """
        if key == "major-newscene":
            if self.datasource_snapshots[key] == 1:
                self.datasources[key] = 0
                return 1
        else:
            return WorldAdapter.get_datasource(self, key)

    def update(self):
        """called on every world simulation step to advance the life of the agent"""

        # we don't move, for now
        self.position = self.world.get_movement_result(self.position, (0, 0))

        #find nearest object to load into the scene
        lowest_distance_to_worldobject = float("inf")
        nearest_worldobject = None
        for key, worldobject in self.world.objects.items():
            # TODO: use a proper 2D geometry library
            distance = island._2d_distance_squared(self.position, worldobject.position)
            if distance < lowest_distance_to_worldobject:
                lowest_distance_to_worldobject = distance
                nearest_worldobject = worldobject

        if self.currentobject is not nearest_worldobject and nearest_worldobject.structured_object_type is not None:
            self.currentobject = nearest_worldobject

            #TODO: load graphics

            self.datasources["major-newscene"] = 1
            logging.getLogger("world").debug("StructuredObjects WA selected new scene: %s",
                                             self.currentobject.structured_object_type)

        #manage the scene
        if self.datatargets['fov_reset'] > 0:
            self.fovea_x = 0
            self.fovea_y = 0

        self.fovea_x += self.datatargets['fov_x']
        self.fovea_y += self.datatargets['fov_y']

        self.datasources["fov-x"] = self.fovea_x
        self.datasources["fov-y"] = self.fovea_y

        #TODO: Fill datasources
