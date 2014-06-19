from micropsi_core.world.worldadapter import WorldAdapter
from micropsi_core.world.minecraft.minecraft_helpers import get_voxel_blocktype
from micropsi_core.world.minecraft import structs

_WIDTH = 10
_HEIGHT = 10

class MinecraftVision(WorldAdapter):

    datasources = {'pixel': 0}
    datatargets = {}



    def update(self):
        """called on every world simulation step to advance the life of the agent"""
        #find pixel

        y = int(self.world.spockplugin.clientinfo.position['y'] + 2)
        bot_z = int(self.world.spockplugin.clientinfo.position['z'])


        minecraft_vision_pixel = ()
        sighted_block = 0

        for x_pixel in range(-_HEIGHT//2, _HEIGHT//2):
            for y_pixel in range(_WIDTH//2, -_WIDTH//2, -1):
                sighted_block = 0
                x = int(self.world.spockplugin.clientinfo.position['x'])
                while sighted_block == 0:
                    sighted_block = get_voxel_blocktype(self, x, y + y_pixel, bot_z + x_pixel)
                    x += 1
                minecraft_vision_pixel = minecraft_vision_pixel + (structs.block_names[str(sighted_block)],)

        self.datasources['pixel'] = sighted_block


        if self.world.data['agents'] is None:
            self.world.data['agents'] = {}
        if self.world.data['agents'][self.uid] is None:
            self.world.data['agents'][self.uid] = {}
        self.world.data['agents'][self.uid]['minecraft_vision_pixel'] = minecraft_vision_pixel