import bpy
import numpy as np
import sys

from bpy.utils import register_class

sys.path.append("/home/tuna/Documents/driving/Vision/syntheticData/")
from utils import blenderTools2 as bt


'''

    Run this script from blender environment to add in UI tools for mannipulating output options

    Current as of 06/16/2023

    TODO:
        Lighting:
            [X] Make tool for switching lights from dynamic and static
            [X] Make tool for attaching light to a new custom constraint, auto make this light dynamic
            [X] Make tool to check lighting on constraint limits
            [X] Add intensity property
        
        Objects:
            [ ] Set up common material list
            [ ] write out configuration file (DR, render count, etc) 
            [ ] fix de-selection issue with "test constraint limits" function
            [ ] refactor custom bbox button, avoid using class nomenclature in name to ID, maybe make this a part of the actual constraint 
                [ ] Ensure synthgen.py looks for child BBoxes when projecting vertices
                [ ] make bbox scale to the actual size of the object
            [ ] Make dust feature
            [ ] Make bounding box visualization projection to camera

    file = open("/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt", 'w')   
'''


'''
Buttons:
    
    [X] add classification:
        - adds custom property with string of class name
    
    [X] add constraints:
        - uses object current position to define a limit
'''



class VIEW3D_PT_synth_object_tools(bpy.types.Panel):

    '''Set up view3D buttons linked to other classes'''
    
    bl_idname = "OBJECT_PT_1"
    bl_label = "Synth Object Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Synth Tools"

    def draw(self, context):
        row = self.layout.row()
        row.operator("object.add_class", text='Add Classification to Object')
        row = self.layout.row()
        row.operator("mesh.add_cube", text='Add Class Bounding Box')
        row = self.layout.row()
        row.operator("object.constraint_test", text='Test Selected Constraint Limits')
'''
cllassificationProperties = [
    ('Class Label', bpy.props.StringProperty(name='label', default='<label>')),
    ('Class Constraint', bpy.props.StringProperty(name='classConstraint', default='<object ID>')),
    ('Part Dependency', bpy.props.StringProperty(name='partDependency', default='<object ID>')),
    ('Dependency Constraint', bpy.props.StringProperty(name='dependencyConstraint', default='<object ID>')),

]
'''

class addClassification(bpy.types.Operator):
    
    bl_idname = "object.add_class"
    bl_label = "Add Classification to object class list"
    bl_description = "Add a new classification to selected object classification can\n" \
                     "be found under -> object data properites -> custom properties"

    def execute(self, context):
        obj = bpy.context.active_object
    
        count = 1
        file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')


    
            
        
        while True:
            try:
                obj.data[f'{count}.classLabel']
                file.write(str('found a class'))
                count += 1
            except:
                break
            
        file.close()        

        obj = bpy.context.active_object

        obj.data[f'{count}.classLabel'] = '<Any>'
        obj.data[f'{count}.constraint'] = '<objectID>'                                                 
        obj.data[f'{count}.customBBox'] = '<objectID>'                                                
        obj.data[f'{count}.partDependency'] = '<objectID>'                                             
        obj.data[f'{count}.dependencyConstraint'] = '<Path, Plane, or Volume ID>'      

        obj.data[f'{count}.split'] = 0.0
        
       
        #bt.visualizeDataStruct(obj.data['1.split'])
        
        return {'FINISHED'}
    
class customSettings(bpy.types.PropertyGroup):
    my_int = bpy.props.IntProperty()
    my_float = bpy.props.FloatProperty()
    my_string = bpy.props.StringProperty()

class MESH_OT_addCustomBoundingCube(bpy.types.Operator):

    '''Adds a wireframe cube that can be used to create a custom bounding box region (when larger context is desired)'''
    
    bl_idname = "mesh.add_cube"
    bl_label = "Add BBox cube"
    bl_description = "Spawn a wire frame cube that may be used to specify a custom\n" \
                     "region of interest for bounding box projection. This cube\n" \
                     "will automatically spawn as a child linked to selected object,\n" \
                     "Booundinng box object will be found under customBBox Collection."
    
    def execute(self, context):
        
        #set desired collection to add to
        obj = bpy.context.active_object
        objName = obj.name

        BBoxCollection = bpy.data.collections['customBBoxes']
        
        #spawn cube with desirable traits
        bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=obj.scale)
        bpy.context.active_object.name = objName + '.customBBox'
        bpy.context.object.display_type = 'WIRE'
        bpy.context.object.hide_render = True
        bpy.context.object.visible_camera = False
        bpy.context.object.visible_diffuse = False
        bpy.context.object.visible_glossy = False
        bpy.context.object.visible_transmission = False
        bpy.context.object.visible_volume_scatter = False
        bpy.context.object.color = (0.00401186, 0.911393, 0.859589, 1)


        BBox = bpy.context.active_object
        
        #remove object from current collection. This is a hacky way to do this, but I couldn't find any documentation
        #   for activating a specific collection. very annoying
        for collection in bpy.data.collections:
            if BBox in collection.objects[:]: collection.objects.unlink(BBox)
            
        #Add class bounding box to proper collection for organization only
        BBoxCollection.objects.link(BBox)

        #make bounding box child to object selected
        BBox.parent = obj
        
        return {'FINISHED'}
        


    

class checkConstraintLimits(bpy.types.Operator):

    bl_idname = 'object.constraint_test'
    bl_label = 'try random location on constraint'
    bl_description = "Select dynamic object first, the constraint object. This will\n" \
                     "move dynamic object to the limits of the constraint object. \n" \
                     "Constraint object may be a 'CURVE', 'PLANE', or 'MESH' with volume."

    def execute(self, context):

        obj = bpy.context.selected_objects[0]
        constraint = bpy.context.selected_objects[1]

        obj.select_set(False)

        #define constraint limit coordinates
        if constraint.type == 'CURVE':
            limitCoords = bt.curveLimits(constraint)

        elif constraint.type == 'MESH' and len(constraint.data.vertices) == 4:
            limitCoords = bt.planarLimits(constraint)

        else:
            limitCoords = bt.volumeLimits(constraint)                
            
        #Update object location to limit coordinates     
        if obj.location in limitCoords:

            idx = limitCoords.index(obj.location)

            if idx == len(limitCoords) - 1: bt.updateAbsPosition(obj, [limitCoords[0]], 0)
            else: bt.updateAbsPosition(obj, [limitCoords[idx + 1]], 0)
        
        else:
            bt.updateAbsPosition(obj, [limitCoords[0]], 0)

        return {'FINISHED'}
    
##############################################
######## Lighting tools ######################
##############################################

class VIEW3D_PT_synth_light_tools(bpy.types.Panel):

    '''Set up view3D buttons linked to other classes'''
    
    bl_idname = "OBJECT_PT_2"
    bl_label = "Synth light Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Synth Tools"

    def draw(self, context):
        row = self.layout.row()
        row.operator("mesh.make_dynamic", text='Make light dynamic')
        row = self.layout.row()
        row.operator("mesh.make_static", text='Make light static')
        row = self.layout.row()
        row.operator("object.make_constraint", text='Pair light to new constraint')
        row = self.layout.row()
        row.operator('object.constraint_test2', text='Test lighting on contraint limits')
        
        row = self.layout.row()
        row.operator("object.add_intensity", text='Set intensity range')

        #row = self.layout.row()
        #row.operator("object.constraint_test", text='Test Selected Constraint Limits')

class makeDynamic(bpy.types.Operator):
    bl_idname = "mesh.make_dynamic"
    bl_label = "Add constraint cube"
    bl_description = "Makes active selected light a dynamic light, and spawns a\n" \
                     "wireframe cube that will be linked as light constraint box\n" \
    
    def execute(self, context):
        
        if bpy.context.active_object.type != 'LIGHT':
            return {'CANCELLED'}
        
        else:
            
            light = bpy.context.active_object

            #move light to dynamic collection
            bpy.data.collections['dynamicLights'].objects.link(light)

            #spawn cube
            bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD', location=light.location)
            constraint = bpy.context.active_object
            constraint.name = light.name + '.constraint'
            constraint.display_type = 'WIRE'
            constraint.hide_render = True
            constraint.visible_camera = False
            constraint.visible_diffuse = False
            constraint.visible_glossy = False
            constraint.visible_transmission = False
            constraint.visible_volume_scatter = False
            
            #unlink objects from current collections
            for collection in bpy.data.collections:
                if light in collection.objects[:]: collection.objects.unlink(light)
                if constraint in collection.objects[:]: collection.objects.unlink(constraint)

            #link to dynamic lights
            bpy.data.collections['dynamicLights'].objects.link(light)
            bpy.data.collections['dynamicLights'].objects.link(constraint)

            #add constraint to light data
            light.data['constraint'] = constraint

            return {'FINISHED'}
        
class makeStatic(bpy.types.Operator):
    bl_idname = "mesh.make_static"
    bl_label = "Add constraint cube"
    bl_description = "Makes active selected light a static light, will remove\n" \
                     "any constraints from the light\n" \
    
    def execute(self, context):
        
        if bpy.context.active_object.type != 'LIGHT':
            return {'CANCELLED'}
        
        else:
            
            light = bpy.context.active_object

            #move light to dynamic collection
            bpy.data.collections['dynamicLights'].objects.unlink(light)
            bpy.data.collections['staticLights'].objects.link(light)

            constraint = light.data['constraint']

            if constraint.name in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[constraint.name], do_unlink=True)

            light.data['constraint'] = None


            return {'FINISHED'}
                     
class makeConstraint(bpy.types.Operator):

    bl_idname = "object.make_constraint"
    bl_label = "make second selection a constraint to first selection"
    bl_description = "Part of interest should be selected first, desired constraint\n" \
                     "object should be selected second"

    def execute(self, context):

        if bpy.context.selected_objects[0].type == 'MESH':
            obj = bpy.context.selected_objects[0]
            light = bpy.context.selected_objects[1]
        elif bpy.context.selected_objects[0].type == 'LIGHT':
            obj = bpy.context.selected_objects[1]
            light = bpy.context.selected_objects[0]

        light.data['constraint'] = obj

        return {'FINISHED'}
    
class checkConstraintLimits2(bpy.types.Operator):

    bl_idname = 'object.constraint_test2'
    bl_label = 'try random location on constraint surface'
    bl_description = "Select dynamic light to be active. This button will\n" \
                     "move dynamic light to the limits of the constraint object. \n" \
                     "Constraint object may be a 'CURVE', 'PLANE', or 'MESH' with volume."

    def execute(self, context): 

        obj = bpy.context.active_object
        
        #define constraint limit coordinates
        try:
            
            constraint = obj.data['constraint']
            
            limitCoords = bt.constraintLimits(constraint)

            if obj.location in limitCoords:

                idx = limitCoords.index(obj.location)

                if idx == len(limitCoords) - 1: bt.updateAbsPosition(obj, [limitCoords[0]], 0)
                else: bt.updateAbsPosition(obj, [limitCoords[idx + 1]], 0)

            else:
                bt.updateAbsPosition(obj, [limitCoords[0]], 0)

            return {'FINISHED'}

        except:
            
            return {'CANCELLED'}

class intensityRange(bpy.types.Operator):

    bl_idname = 'object.add_intensity'
    bl_label = 'add intensity range to light object'
    bl_description = "Use this to add an intensity range to the selected\n" \
                     "light. This will only be used when lighting is active\n" \
                     "in domain randomization"
    
    def execute(self, context): 

        light = bpy.context.active_object

        bt.visualizeDataStruct(light.data)
        currentPower = light.data.energy
        light.data['intensityRange'] = [currentPower, currentPower]

        return {'FINISHED'}


###################################################
#       Inspection tools ##
###################################################

class VIEW3D_PT_synth_inspection_tools(bpy.types.Panel):

    '''Set up view3D buttons linked to other classes'''
    
    bl_idname = "OBJECT_PT_3"
    bl_label = "Synth inspection Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Synth Tools"

    def draw(self, context):
        row = self.layout.row()
        row.operator("object.make_inspection", text='Inspect object (txt file)')
        row = self.layout.row()
        row.operator("object.dat_type", text='Inspect object type (txt file)')

class inspect(bpy.types.Operator):

    bl_idname = 'object.make_inspection'
    bl_label = 'add intensity range to light object'
    bl_description = "Use this to add an intensity range to the selected\n" \
                     "light. This will only be used when lighting is active\n" \
                     "in domain randomization"
    
    def execute(self, context):
        obj = bpy.context.active_object
        bt.visualizeDataStruct(obj.data['1.objectClassification'].values())

        for key in obj.data['1.objectClassification'].keys():

            print(str(key))

        return {'FINISHED'}
    
class dataType(bpy.types.Operator):
    bl_idname = 'object.dat_type'
    bl_label = 'add intensity range to light object'
    bl_description = "Use this to add an intensity range to the selected\n" \
                     "light. This will only be used when lighting is active\n" \
                     "in domain randomization"
    
    def execute(self, context):
        file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')
    
        file.write(str(type(bpy.context.active_object.data.texture_mesh)))
        file.close()

        return {'FINISHED'}

def register():
    
    #object tools
    bpy.utils.register_class(VIEW3D_PT_synth_object_tools)
    bpy.utils.register_class(MESH_OT_addCustomBoundingCube)
    bpy.utils.register_class(addClassification)
    bpy.utils.register_class(checkConstraintLimits)
    bpy.utils.register_class(customSettings)

    #lighting tools
    bpy.utils.register_class(VIEW3D_PT_synth_light_tools)
    bpy.utils.register_class(makeDynamic)
    bpy.utils.register_class(makeStatic)
    bpy.utils.register_class(makeConstraint)
    bpy.utils.register_class(checkConstraintLimits2)
    bpy.utils.register_class(intensityRange)

    #inspection tools
    bpy.utils.register_class(VIEW3D_PT_synth_inspection_tools)
    bpy.utils.register_class(inspect)
    bpy.utils.register_class(dataType)
    
    
def unregister():
    
    bpy.utils.unregister_class(VIEW3D_PT_synth_object_tools)
    

    bpy.utils.unregister_class(MESH_OT_addCustomBoundingCube)
    bpy.utils.unregister_class(addClassification)
    bpy.utils.unregister_class(checkConstraintLimits)

    bpy.utils.unregister_class(VIEW3D_PT_synth_light_tools)
    bpy.utils.unregister_class(makeConstraint)
    bpy.utils.unregister_class(checkConstraintLimits2)
    
    
if __name__ == "__main__":
    
    register()
    


    '''
    file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')
    
    file.write(str(bpy.context.active_object.data['Part Dependency']))
    file.close()'''