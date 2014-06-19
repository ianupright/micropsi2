/*
 * viewer for the world.
 */

worldscope = paper;

var canvas = $('#world');

var HEIGHT = 10
var WIDTH = 10

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
		
								$("#minecraft_vision_" + x + "_" + y).attr("src", "/static/minecraft/block_textures/" + minecraft_pixel[x+y*height] + ".png");
		
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


    var world_div = $("#world_editor .editor_field.span9")
	
	var table = "<table>";
	
	var height = HEIGHT;
	var width = WIDTH;
	
	for (var x = 0; x < height; x++){
		table = table + "<tr>";
		for (var y = 0; y < width; y++){
		
			table = table + '<td><img id="minecraft_vision_' + x + '_' + y + '"></td>';
		
		}
		table = table + "</tr>";
	}
	
	table = table + "</table>";
	
	world_div.html(table);
	
    api.call('get_world_properties', {
        world_uid: currentWorld
    }, success = function (data) {
        refreshWorldView();
       }, error = function (data) {
        $.cookie('selected_world', '', {expires: -1, path: '/'});
        dialogs.notification(data.Error, 'error');
    });
}

function updateViewSize() {
    view.draw(true);
}

