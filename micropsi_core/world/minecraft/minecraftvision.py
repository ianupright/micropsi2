from micropsi_core.world.worldadapter import WorldAdapter
from micropsi_core.world.minecraft.minecraft_helpers import get_voxel_blocktype
from micropsi_core.world.minecraft import structs
import math

_WIDTH = 20
_HEIGHT = 20
_VIEW_ANGLE = 60

class MinecraftVision(WorldAdapter):

    datasources = {'pixel': 0}
    datatargets = {}



    def update(self):
        """called on every world simulation step to advance the life of the agent"""
        #find pixel

        bot_x = int(self.world.spockplugin.clientinfo.position['x'])
        y = int(self.world.spockplugin.clientinfo.position['y'] + 2)
        bot_z = int(self.world.spockplugin.clientinfo.position['z'])


        minecraft_vision_pixel = ()
        sighted_block = 0

        for x_pixel in range(-_HEIGHT//2, _HEIGHT//2):
            for y_pixel in range(_WIDTH//2, -_WIDTH//2, -1):
                x_angle = x_pixel * _VIEW_ANGLE // -_HEIGHT
                y_angle = y_pixel * _VIEW_ANGLE // -_HEIGHT
                x_blocks_per_distance = math.tan(x_angle)
                y_blocks_per_distance = math.tan(y_angle)
                sighted_block = 0
                distance = 0
                while sighted_block == 0:
                    #print("y + int(y_blocks_per_distance * distance) is " + str(y + int(y_blocks_per_distance * distance)))
                    sighted_block = get_voxel_blocktype(self, bot_x + distance, y + int(y_blocks_per_distance * distance), int(x_blocks_per_distance * distance) + bot_z)
                    distance += 1
                print("found " + structs.block_names[str(sighted_block)] + " at " + str((bot_x + distance, y + int(y_blocks_per_distance * distance), int(x_blocks_per_distance * distance) + bot_z)))
                minecraft_vision_pixel = minecraft_vision_pixel + (structs.block_names[str(sighted_block)],  distance)

        self.datasources['pixel'] = sighted_block


        if self.world.data['agents'] is None:
            self.world.data['agents'] = {}
        if self.world.data['agents'][self.uid] is None:
            self.world.data['agents'][self.uid] = {}
        self.world.data['agents'][self.uid]['minecraft_vision_pixel'] = minecraft_vision_pixel



