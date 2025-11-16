# Author: ClusterTrace
# Date: November 16, 2025

bl_info = {
    "name": "Force Modal Tool Addon",
    "author": "ClusterTrace",
    "blender": (4,5,0),
    "description": "An addon that adds a tool to the View 3D toolbar that creates a forcefield on vertices for the use case of dragging active cloth sims",
    "category": "Object",
}

import bpy
import mathutils
from bpy.types import WorkSpaceTool
from bpy_extras import view3d_utils

# The main tool class
class ForceCreationTool(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'

    # Tool identification
    bl_idname = "my_tool.force_creator"
    bl_label = "Create force on a surface"
    bl_description = "Click on a mesh to create an forcefield at that location"
    bl_icon = "ops.transform.transform"
    bl_widget = None
    bl_keymap = (
        ("object.force_modal_operator", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    )

    def draw_settings(context, layout, tool): # this tells what to show in the active tool panel under Tool
        props = tool.operator_properties("object.force_modal_operator") # example to get it to show the properties of an operator
        layout.prop(props, "strength")
        layout.prop(props, "maxDistance")
        layout.prop(props, "minDistance")
        layout.prop(props, "falloffPower")
        layout.prop(props, "placeOnVertex")

class ForceModalOperator(bpy.types.Operator):
    bl_idname = "object.force_modal_operator"
    bl_label = "Force Modal Operator"
    bl_options = {'REGISTER', 'UNDO'}

    maxDistance : bpy.props.FloatProperty(
        name="Max Distance",
        description = "Max distance the force affects",
        default=0.05,
        min=0.001,
        max=1
    )
    
    minDistance : bpy.props.FloatProperty(
        name="Minimum Distance",
        description="Minimum distance the force affects",
        default=0.001,
        min=0.001,
        max=1
    )
    
    strength : bpy.props.FloatProperty(
        name="Strength",
        description="Strength or power of the force field's push (if positive) or pull (if negative)",
        default= -500,
        min=-1000,
        max=1000
    )
    
    falloffPower : bpy.props.FloatProperty(
        name="Falloff Power",
        description="How quickly the strength of the force field falls off",
        default= 0,
        min=0,
        max=5
    )
    
    placeOnVertex : bpy.props.BoolProperty(
        name="Use Closest Vertex",
        description="Whether to place the forcefield on the closest vertex",
        default= True,
    )
    
    def __init__(self, *args, **kwargs): # triggered when the modal is started
        super().__init__(*args, **kwargs)
        #print("Start")
        
    
    #def __del__(self): # triggered after the model is finished
        #print("End")
        #super().__del__()
        
    def execute(self, context):
        tempViewportLoc = self.viewportBasis.inverted() @ self.forceEmitter.location # Transform world location to viewport basis
        
        # Move the force emitter object with cursor movement
        tempViewportLoc[0] = tempViewportLoc[0] + (self.valueX - self.valueXPrev) / 100
        tempViewportLoc[1] = tempViewportLoc[1] + (self.valueY - self.valueYPrev) / 100
        
        tempWorldLoc = self.viewportBasis @ tempViewportLoc # Transform viewport basis to world location
        self.forceEmitter.location = tempWorldLoc
        
        return {'FINISHED'}
    
    def modal(self, context, event):
        if event.type =='MOUSEMOVE': # Apply
            # updates the values recording current mouse position and previous position
            self.valueXPrev = self.valueX
            self.valueYPrev = self.valueY
            self.valueX = event.mouse_x
            self.valueY = event.mouse_y
            self.execute(context)
        elif event.type == 'LEFTMOUSE': # Confirm
            setSelectedObject(self.forceEmitter)
            bpy.ops.object.delete() # deletes the the force object
            setSelectedObject(self.obj) # sets the selected object back to what it was
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}: # Cancel
            # Revert all changes that have been made
            setSelectedObject(self.forceEmitter)
            bpy.ops.object.delete() # deletes the the force object
            setSelectedObject(self.obj) # sets the selected object back to what it was
            return{'CANCELLED'}
        
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        self.valueX_initial = event.mouse_x
        self.valueY_initial = event.mouse_y
        self.valueX = event.mouse_x
        self.valueY = event.mouse_y
        self.valueXPrev = event.mouse_x
        self.valueYPrev = event.mouse_y
        self.viewportBasis = get_viewport_basis(context)
        
        #new stuff to do at modal start
        obj = context.object
        # Perform raycast
        hit, location, normal, face_index, raycastObj = raycast_from_mouse(context, event)

        if hit and (obj == raycastObj):
            # gets updated positions of object vertices
            dg = context.evaluated_depsgraph_get()
            dgObject = obj.evaluated_get(dg)

            closest_vert_co = mathutils.Vector((0, 0, 0)) # defaults to the origin of the world
            if (self.placeOnVertex and obj.type == 'MESH'): # Find closest vertex to hit location
                closest_vert_co, closest_vert_id = find_closest_vertex(dgObject, location)
            else: # or simply uses where the ray hit
                if (self.placeOnVertex): # notes error if was supposed to use closest vertex but couldn't
                    self.report({'WARNING'}, "No mesh object selected to find closest vertex. Defaulting to ray hit location.")
                closest_vert_co = location
        
            #self.vert = closest_vert_id
            self.vertCo = closest_vert_co
            self.obj = obj
            
            # add force emitter: bpy.ops.object.effector_add(type='FORCE', enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
            bpy.ops.object.effector_add(type='FORCE', enter_editmode=False, align='WORLD', location=closest_vert_co, scale=(1, 1, 1))
            self.forceEmitter = context.active_object
            # edit the force emitter's settings so it pulls using values controlling parts like force, size, falloff, max distance, etc which later can be made to be tool settings
            self.forceEmitter.field.use_max_distance = (self.maxDistance > 0)
            self.forceEmitter.field.distance_max = self.maxDistance
            self.forceEmitter.field.use_min_distance = (self.minDistance > 0)
            self.forceEmitter.field.distance_min = self.minDistance
            self.forceEmitter.field.strength = self.strength
            self.forceEmitter.field.falloff_power = self.falloffPower
            
            self.execute(context)
            
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No surface hit on selected object. Click on a selected object.")
            return {'FINISHED'}

# Only needed if you want to add into a dynamic menu
#def menu_func(self, context):
#    self.layout.operator(ForceModalOperator.bl_idname, text="Force Modal Operator")
    
# Helper methods: -------------------------------------------
def raycast_from_mouse(context, event):
    """
    Performs a raycast from the mouse position into the scene.
    Returns: (hit, location, normal, face_index, object)
    """
    # Get the region and region_3d
    region = context.region
    region_3d = context.space_data.region_3d

    # Get mouse coordinates
    mouse_coord = (event.mouse_region_x, event.mouse_region_y)

    # Get the ray from the viewport
    view_vector = view3d_utils.region_2d_to_vector_3d(region, region_3d, mouse_coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, region_3d, mouse_coord)

    # Perform scene raycast
    result = context.scene.ray_cast(
        context.view_layer.depsgraph,
        ray_origin,
        view_vector
    )

    # result is a tuple: (success, location, normal, face_index, object, matrix)
    success = result[0]
    location = result[1]
    normal = result[2]
    face_index = result[3]
    obj = result[4]

    return success, location, normal, face_index, obj


def find_closest_vertex(obj, world_location):
        """
        Finds the closest vertex on the mesh to the given world location.
        Returns: (vertex_world_coordinates, vertex_index)
        """
        # Get the object's mesh data
        mesh = obj.data

        # Transform world location to object's local space
        local_location = obj.matrix_world.inverted() @ world_location

        # Find closest vertex
        min_distance = float('inf')
        closest_vert_id = -1
        closest_vert_local = None

        for i, vert in enumerate(mesh.vertices):
            distance = (vert.co - local_location).length
            if distance < min_distance or i == 0: # if smaller or first index (to ensure using values from model instead of just hoping infinity is good enough)
                min_distance = distance
                closest_vert_id = i
                closest_vert_local = vert.co.copy()

        # Transform back to world space
        closest_vert_world = obj.matrix_world @ closest_vert_local

        return closest_vert_world, closest_vert_id

def vertexGroupExist(obj, vertexGroupName):
    """
    Returns a boolean for whether a given vertex group exists on an object
    """
    for i in obj.vertex_groups:
        if i.name == vertexGroupName:
            return True
    return False

def vertexInVertexGroup(obj, vertexID, vertexGroupName):
    """
    Returns a boolean for whether a given vertex is a part of a vertex group
    """
    for i in obj.data.vertices[vertexID].groups:
        if i.name == vertexGroupName:
            return True
    return False

def setSelectedObject(obj):
    bpy.ops.object.select_all(action='DESELECT'); # deselects everything
    #bpy.context.selected_objects.append(obj) # selects the object
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj; # sets active object

def get_viewport_basis(context):
    """
    Get a basis matrix where:
    - X axis: horizontal of viewport (right)
    - Y axis: vertical of viewport (up)
    - Z axis: facing viewport (towards camera)
    """
    region = context.region
    rv3d = context.region_data
    
    # Get the view matrix (camera transformation)
    view_mat = rv3d.view_matrix.inverted()
    
    # Extract basis vectors from view matrix
    x_axis = view_mat.col[0].xyz.normalized()# - X axis in viewport
    y_axis = view_mat.col[1].xyz.normalized() # - Y axis in viewport
    z_axis = -view_mat.col[2].xyz.normalized() # - Z axis, negated to make axis point towards view/camera
    
    # Create basis matrix from the view matrix vectors
    basis = mathutils.Matrix((
        x_axis.to_4d(),
        y_axis.to_4d(),
        z_axis.to_4d(),
        mathutils.Vector((0, 0, 0, 1))
    ))
    basis.transpose()
    
    return basis

# Register and unregister functions
def register():
    #bpy.utils.register_tool(ForceCreationTool, after={"builtin.cursor"}, separator=True, group=False)
    bpy.utils.register_tool(ForceCreationTool, separator=True, group=False)
    bpy.utils.register_class(ForceModalOperator)
    #bpy.types.VIEW3D_MT_object.append(menu_func) # add to the object menu (required to also use F3 search "Modal Operator" for quick access)
    #bpy.ops.object.modal_operator('INVOKE_DEFAULT') # test call the modal operator directly


def unregister():
    bpy.utils.unregister_class(ForceModalOperator)
    bpy.utils.unregister_tool(ForceCreationTool)


if __name__ == "__main__":
    register()