/*
 * viewer for the world.
 */
worldscope = paper;

var HEIGHT = 20;
var WIDTH = 20;

objects = {};
symbols = {};
agents = {};

currentWorld = $.cookie('selected_world') || null;

objectLayer = new Layer();
objectLayer.name = 'ObjectLayer';

currentWorldSimulationStep = -1;

if (currentWorld) {
    setCurrentWorld(currentWorld);
}

worldRunning = false;

refreshWorldView = function () {


    worldscope.activate();
    var minecraft_pixel;

    api.call('get_world_view', {
            world_uid: currentWorld,
            step: currentWorldSimulationStep
        },
        function (data) {
            if (jQuery.isEmptyObject(data)) {
                if (worldRunning) {
                    setTimeout(refreshWorldView, 100);
                }
                return null;
            }
            currentWorldSimulationStep = data.current_step;
            $('#world_step').val(currentWorldSimulationStep);
            $('#world_status').val(data.status_message);
            // treat agents and objects the same
            for (var key in data.agents) {



                if (data.agents[key].minecraft_vision_pixel) {
                    minecraft_pixel = data.agents[key].minecraft_vision_pixel;

                    var height = HEIGHT;
                    var width = WIDTH;

                    for (var x = 0; x < height; x++) {

                        for (var y = 0; y < width; y++) {
                            var raster = new Raster('mc_block_img_' + minecraft_pixel[(x + y * height) * 2]);
                            raster.position = new Point(32 * y, 32 * x);
                            raster.scale(2 * 1 / minecraft_pixel[(x + y * height) * 2 + 1]);

                        }
                    }

                    break;

                }

            }
            updateViewSize();
            if (worldRunning) {
                refreshWorldView();
            }
        }, error = function (data) {
            $.cookie('selected_world', '', {
                expires: -1,
                path: '/'
            });
            dialogs.notification(data.Error, 'error');
        }
    );



}

function addAgent(worldobject) {
    if (!(worldobject.uid in objects)) {
        renderObject(worldobject);
        objects[worldobject.uid] = worldobject;
    } else {
        redrawObject(objects[worldobject.uid]);
    }
    objects[worldobject.uid] = worldobject;
    agentsList.html(agentsList.html() + '<tr><td><a href="#" data="' + worldobject.uid + '" class="world_agent">' + worldobject.name + ' (' + worldobject.type + ')</a></td></tr>');
    return worldobject;
}

function setCurrentWorld(uid) {
    currentWorld = uid;
    $.cookie('selected_world', currentWorld, {
        expires: 7,
        path: '/'
    });
    loadWorldInfo();
}

function loadWorldInfo() {

    var all_images = ""

    var editor_div = $("#world_forms");

    $.getScript('/static/minecraft/minecraft_struct.js', function () {
        for (var i = -1; i < 173; i++) {

            var block_name = block_names["" + i];
            all_images = all_images + '<img id="mc_block_img_' + block_name + '" src="/static/minecraft/block_textures/' + block_name + '.png">';

            editor_div.html('<div style="height:0; overflow: hidden">' + all_images + '</div>');
        }
    });

    editor_div.html('<div style="height:0; overflow: hidden">' + all_images + '</div>');

    api.call('get_world_properties', {
        world_uid: currentWorld
    }, success = function (data) {
        refreshWorldView();
    }, error = function (data) {
        $.cookie('selected_world', '', {
            expires: -1,
            path: '/'
        });
        dialogs.notification(data.Error, 'error');
    });
};

function updateViewSize() {
    view.draw(true);
}