/*
 * viewer for the world.
 */

worldscope = paper;

var canvas = $('#world');

var block_names = {"-1": "nothing_sky",
                            "0": "nothing_sky",
                            "1": "stone",
                            "2": "grass_top",
                            "3": "dirt",
                            "4": "stonebrick",
                            "5": "wood",
                            "6": "sapling",
                            "7": "bedrock",
                            "8": "water",
                            "9": "water",
                            "10": "lava",
                            "11": "lava",
                            "12": "sand",
                            "13": "gravel",
                            "14": "oreGold",
                            "15": "oreIron",
                            "16": "oreCoal",
                            "17": "tree_top",
                            "18": "leaves",
                            "19": "sponge",
                            "20": "glass",
                            "21": "oreLapis",
                            "22": "blockLapis",
                            "23": "furnace_top",
                            "24": "sandstone_top",
                            "25": "musicBlock",
                            "26": "bed_feet_top",
                            "27": "goldenRail_powered",
                            "28": "detectorRail_on",
                            "29": "piston_inner_top",
                            "30": "web",
                            "31": "fern",
                            "32": "deadbush",
                            "33": "piston_top",
                            "34": "piston_top_sticky",
                            "35": "cloth_0",
                            "37": "flower",
                            "38": "rose",
                            "39": "mushroom_brown",
                            "40": "mushroom_red",
                            "41": "blockGold",
                            "42": "blockIron",
                            "43": "stoneslab_top",
                            "44": "stoneslab_top",
                            "45": "brick",
                            "46": "tnt_top",
                            "47": "wood",
                            "48": "stoneMoss",
                            "49": "obsidian",
                            "50": "torch",
                            "51": "fire_0",
                            "52": "mobSpawner",
                            "53": "wood",
                            "55": "redstoneDust_line",
                            "56": "oreDiamond",
                            "57": "blockDiamond",
                            "58": "workbench_front",
                            "59": "crops_7",
                            "60": "dirt",
                            "61": "furnace_front",
                            "62": "furnace_front_lit",
                            "63": "wood",
                            "64": "doorWood_lower",
                            "65": "ladder",
                            "66": "rail",
                            "67": "stonebrick",
                            "68": "wood",
                            "69": "stonebrick",
                            "70": "stone",
                            "71": "doorIron_lower",
                            "72": "wood",
                            "73": "oreRedstone",
                            "74": "oreRedstone",
                            "75": "redtorch",
                            "76": "redtorch_lit",
                            "77": "stone",
                            "78": "snow",
                            "79": "ice",
                            "80": "snow",
                            "81": "cactus_top",
                            "82": "clay",
                            "83": "reeds",
                            "84": "jukebox_top",
                            "85": "wood",
                            "86": "ppumpkin_face",
                            "87": "hellrock",
                            "88": "hellsand",
                            "89": "lightgem",
                            "91": "pumpkin_jack",
                            "92": "cake_inner",
                            "93": "redtorch",
                            "94": "redtorch_lit",
                            "95": "cactus_bottom",
                            "96": "trapdoor",
                            "97": "stone",
                            "98": "stonebricksmooth",
                            "99": "mushroom_skin_stem",
                            "100": "mushroom_skin_stem",
                            "101": "fenceIron",
                            "102": "glass",
                            "103": "melon_top",
                            "104": "stem_bent",
                            "105": "bentStem=stem_bent",
                            "106": "vine",
                            "107": "wood",
                            "108": "brick",
                            "109": "stonebricksmooth",
                            "110": "mycel_top",
                            "111": "waterlily",
                            "112": "netherBrick",
                            "113": "netherBrick",
                            "114": "netherBrick",
                            "115": "netherStalk_2",
                            "116": "enchantment_bottom",
                            "117": "brewingStand",
                            "118": "water",
                            "120": "endframe_eye",
                            "121": "whiteStone",
                            "122": "dragonEgg",
                            "123": "redstoneLight",
                            "124": "redstoneLight_lit",
                            "125": "wood",
                            "127": "cocoa_2",
                            "128": "sandstone_side",
                            "129": "oreEmerald",
                            "131": "wood",
                            "133": "blockEmerald",
                            "134": "wood_spruce",
                            "135": "wood_birch",
                            "136": "wood_jungle",
                            "137": "commandBlock",
                            "138": "obsidian",
                            "139": "stonebrick",
                            "139": "stoneMoss",
                            "141": "carrots_3",
                            "142": "potatoes_2",
                            "143": "wood",
                            "145": "anvil_top_damaged_2",
                            "147": "blockGold",
                            "148": "blockIron",
                            "149": "comparator_lit",
                            "150": "redtorch_lit",
                            "151": "daylightDetector_side",
                            "152": "blockRedstone",
                            "153": "netherquartz",
                            "154": "hopper_inside",
                            "155": "quartzblock_top",
                            "156": "quartzblock_top",
                            "157": "activatorRail_powered",
                            "158": "dropper_front",
                            "159": "clayHardenedStained_0",
                            "170": "hayBlock_top",
                            "171": "cloth_0",
                            "171": "cloth_1",
                            "172": "clayHardened",
                            "173": "oreCoal"}

var HEIGHT = 20;
var WIDTH = 20;

var viewProperties = {
    frameWidth: 1445,
    zoomFactor: 1,
    objectWidth: 12,
    lineHeight: 15,
    objectLabelColor: new Color("#94c2f5"),
    objectForegroundColor: new Color("#000000"),
    fontSize: 10,
    symbolSize: 14,
    highlightColor: new Color("#ffffff"),
    gateShadowColor: new Color("#888888"),
    shadowColor: new Color("#000000"),
    shadowStrokeWidth: 0,
    shadowDisplacement: new Point(0.5, 1.5),
    innerShadowDisplacement: new Point(0.2, 0.7),
    padding: 3,
    label: {
        x: 10,
        y: -10
    }
};

objects = {};
symbols = {};
agents = {};

currentWorld = $.cookie('selected_world') || null;

objectLayer = new Layer();
objectLayer.name = 'ObjectLayer';

currentWorldSimulationStep = -1;

var world_data = null;

if (currentWorld) {
    setCurrentWorld(currentWorld);
}

worldRunning = false;

refreshWorldView = function(){


		worldscope.activate();
		var minecraft_pixel;

	    api.call('get_world_view',
	        {world_uid: currentWorld, step: currentWorldSimulationStep},
	        function(data){
	            if(jQuery.isEmptyObject(data)){
	                if(worldRunning){
	                    setTimeout(refreshWorldView, 100);
	                }
	                return null;
	            }
	            currentWorldSimulationStep = data.current_step;
	            $('#world_step').val(currentWorldSimulationStep);
	            $('#world_status').val(data.status_message);
	            // treat agents and objects the same
	            for(var key in data.agents){



					if (data.agents[key].minecraft_vision_pixel){
						minecraft_pixel = data.agents[key].minecraft_vision_pixel;

						var height = HEIGHT;
						var width = WIDTH;

						for (var x = 0; x < height; x++){

							for (var y = 0; y < width; y++){
                                 var raster = new Raster('mc_block_img_' + minecraft_pixel[(x+y*height)*2]);
                                    raster.position = new Point(32*y, 32*x);
                                    raster.scale(2*1/minecraft_pixel[(x+y*height)*2+1]);

							}
						}

						break;

					}

				}
	            updateViewSize();
	            if(worldRunning){
	                refreshWorldView();
	            }
	        }, error=function(data){
	            $.cookie('selected_world', '', {expires:-1, path:'/'});
	            dialogs.notification(data.Error, 'error');
	        }
	    );



}

function addAgent(worldobject){
    if(! (worldobject.uid in objects)) {
        renderObject(worldobject);
        objects[worldobject.uid] = worldobject;
    } else {
        redrawObject(objects[worldobject.uid]);
    }
    objects[worldobject.uid] = worldobject;
    agentsList.html(agentsList.html() + '<tr><td><a href="#" data="'+worldobject.uid+'" class="world_agent">'+worldobject.name+' ('+worldobject.type+')</a></td></tr>');
    return worldobject;
}

function setCurrentWorld(uid) {
    currentWorld = uid;
    $.cookie('selected_world', currentWorld, {expires: 7, path: '/'});
    loadWorldInfo();
}

function loadWorldInfo() {

    var all_images = ""

   var editor_div = $("#world_forms");

      for(var i = -1; i < 173; i++) {

     var block_name = block_names["" + i];
     all_images = all_images + '<img id="mc_block_img_' + block_name + '" src="/static/minecraft/block_textures/' + block_name + '.png">';

    }

	editor_div.html('<div style="height:0; overflow: hidden">' + all_images + '</div>');

    api.call('get_world_properties', {
        world_uid: currentWorld
    }, success = function (data) {
        refreshWorldView();
       }, error = function (data) {
        $.cookie('selected_world', '', {expires: -1, path: '/'});
        dialogs.notification(data.Error, 'error');
    });
};

function updateViewSize() {
    view.draw(true);
}




