import bpy
from bpy_extras.object_utils import world_to_camera_view
import csv
import numpy as np
import copy
import time
import random
import sys
import json

import bmesh
import mathutils


sys.path.append("/home/tuna/Documents/driving/Vision/syntheticData/")
from utils import blenderTools2 as bt


''' This script must be run from within blender scripting environment

    Current as of 06/22/2023
        Blender:    3.5
        python:     3.7

        associated files: buildDataSet5.py, applyBBox5.py
    
        TODO:
            [X] figure out how to set object contraints easily
            [ ] verify that all refactor works with simple dataset
            [X] add compute time remaining to terminal output
            [X] set up domain randomization params, set up collections for each object
            [ ] figure out how to pull from material library through bpy
            [ ] add a key stroke break command
            [ ] add render start warnings if things are missing (eg, if Lighting DR is true but no lighting BBox active etc)

'''


class lighting():

    ''' class for storing all properties of lights within the scene'''

    def __init__(self):

        self.static = []
        self.dynamic = dict()
        
        for light in bpy.data.collections['dynamicLights'].objects:

            if light.type != "LIGHT": continue
            
            self.dynamic[light.name] = dict()
            
            self.dynamic[light.name]['initLoc'] = copy.copy(light.location)

            try:self.dynamic[light.name]['constraint'] = light.data['constraint']
            except: print(f'Warning, no constraint provided for {light.name}')

            self.dynamic[light.name]['initIntensity'] = copy.copy(light.data.energy)
            
            #check if intensity range specified
            try: self.dynamic[light.name]['intensityRange'] = light.data['intensityRange'] #[min, max]
            except: self.dynamic[light.name]['intensityRange'] = None

        for light in bpy.data.collections['staticLights'].objects:
            #weed out any erroneous 
            if light.instance_type != 'LIGHT': pass
            self.static.append(light)

    def updateIntensity(self, light, domainRandomization):

        #break if light is not in dynamic collection
        if light.name not in self.dynamic.keys():
            return
        
        #break if light does not have intensity range set
        if self.dynamic[light.name]['intensityRange'] == None:
            return

        randomType = domainRandomization['lighting']['intensity']['random']['method']

        low = self.dynamic[light.name]['intensityRange'][0]
        high = self.dynamic[light.name]['intensityRange'][1]

        #normal distribution
        if randomType == 'normal':

            sigmaMultiplier = domainRandomization['lighting']['intensity']['random']['sigma']
            sigma = (high - low)*sigmaMultiplier

            newIntensity = np.random.default_rng().normal(loc=self.dynamic[light.name]['initIntensity'], scale=sigma, size = 1)

            #clamp to constraint limit
            newIntensity = np.clip(newIntensity, low, high)

        #uniform distribution
        else:
            low = self.dynamic[light.name]['intensityRange'][0]
            high = self.dynamic[light.name]['intensityRange'][1]
            newIntensity = random.uniform(low, high)

        light.data.energy = newIntensity

        return
            

class camera():

    def __init__(self):
        
        self.cam = bpy.data.objects['camera']
        self.initLoc = copy.copy(bpy.data.objects['camera'].location)
        self.initRot = copy.copy(bpy.data.objects['camera'].rotation_euler)
        self.constraint = bpy.data.objects['camera.constraint']
        self.tracker = bpy.data.objects['camera.focalPt']
        self.translationPostions = []
        self.rotationPostions = []

    def toggleTracking(self):

        '''cann be used to turn on/off tracking at arbitrary point in data collection'''

        #if there is a constraint, remove it #TODO: verify the removing a constraint works
        try:
            tracking = self.cam.constraints.remove('TRACK_TO')
            self.cam.constraints.remove(tracking)

        #else, add the tracking constraint
        except:
            tracking = self.cam.constraints.new(type='TRACK_TO')
            tracking.target = self.tracker
            tracking.track_axis = 'TRACK_NEGATIVE_Z'
            tracking.up_axis = 'UP_Y'




class classifications():

    ''' dictionary storing all classification data, I wanted to build this class to handle the multi part values in the data.
        right now, the dictionary values that blender allows you to store are all strings. Here I take those strings that identify
        objects and i make a new dictionary where the value is the actual object pointer. This is slightly easier to work with
        than the blender dictionaries '''

    def __init__(self):

        self.classObjects = dict()
       
        #iterate through objects looking for ones with a classification
        for obj in bpy.data.objects:
            count = 1
           
            try:
                obj.data[f'1.classLabel']
                self.classObjects[obj.name] = dict()

                #look through object data in blender class, search for all classifications associated with part
                while True:
                    try:
                        label = obj.data[f'{count}.classLabel']
                        if label == '<Any>':
                            print(f'found class for {obj.name} but no label defined')
                            break
                    except:
                        break  
                    
                    split = obj.data[f'{count}.split']      #float
                    if not 0 < split <= 1:
                        print(f'found class for {obj.name} with no split defined, must define split value (0., 1.]')
                        break

                    constraintID = obj.data[f'{count}.constraint']              #<string> should be the name of an object in the scene
                    if constraintID != '<objectID>': constraintObj = bpy.data.objects[constraintID]     #if the user defined this, look for that object and save the pointer
                    else: constraintObj = None
                

                    customBBoxID =  obj.data[f'{count}.customBBox']
                    if customBBoxID != '<objectID>': customBBoxObj = bpy.data.objects[customBBoxID]
                    else: customBBoxObj = None
                
            
                    partDependencyID = obj.data[f'{count}.partDependency']
                    if partDependencyID != '<objectID>': partDependencyObj = bpy.data.objects[partDependencyID]
                    else: partDependencyObj = None
                
                    dependencyConstraintID = obj.data[f'{count}.dependencyConstraint']
                    if dependencyConstraintID != '<Path, Plane, or Volume ID>': dependencyConstraintObj = bpy.data.objects[dependencyConstraintID]
                    else: 
                        dependencyConstraintObj = None
                        if partDependencyObj != None:
                            print('Warning: part dependency defined but no dependency constraint provided')
                            break

                    self.classObjects[obj.name][count] = {
                                                            'label':                label,
                                                            'split':                split,
                                                            'constraint':           constraintObj,
                                                            'positions':            [],
                                                            'customBBox':           customBBoxObj,

                                                            'partDependency':       partDependencyObj,
                                                            'dependencyConstraint': dependencyConstraintObj,
                                                            'dependencyPositions':  []
                                                            }
                    
                    
                    count += 1
                
            except: pass  

              


class objects():

    def __init__(self):

        self.static = []
        self.dynamic = dict()
        
        for obj in bpy.data.collections['dynamicParts'].objects:

            self.dynamic[obj.name] = {
                                            'initLoc':      copy.copy(obj.location),
                                            'initRot':      copy.copy(obj.rotation_euler),
                                            'material':     obj.data.materials
                                        }
            

def main(renderInfo, cameraParams, domainRandomization, paths):
    print('')
    
    #debugging
    #debugFile = open("/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt", 'w')

    file = open(paths['csv'] + paths['fileName'] + ".csv", "w")
    data = csv.writer(file)

    #top row column names
    labelID = ["use", "fileName", "classification", "xMin", "yMin", None, None, "xMax", "yMax", None, None, "camX", "camY", "camZ"]
    data.writerow(labelID)

    renderCount = renderInfo['count']  #int

    #define blender scene
    scene = bpy.context.scene

    #gather current resolution for multiplication later on
    res_x = scene.render.resolution_x
    res_y = scene.render.resolution_y

    ############################################
    ### <<<  Define all Basic Part info  >>> ###
    ############################################

    objs = objects()
    classObjs = classifications()
   

    
    ##############################################
    ### <<< Define all lighting Properties >>> ###
    ##############################################

    lights = lighting()
     
    #async io terminate process task
    

    ############################################
    ### <<< Define all Camera Properties >>> ###
    ############################################

    cam = camera()
   

    #check and handle tracking
    if cameraParams['tracking']['active']: 
        cam.toggleTracking()

    #generate dynamic camera translation positions
    if cameraParams['translation']['active']:
        randomType = cameraParams['translation']['random']['method']
        
        cam.translationPostions = bt.generatePositions(constraintObj=      cam.constraint, 
                                                        dynamicObj=     cam.cam, 
                                                        randomType=     randomType, 
                                                        count=          renderCount
                                                        )
        #storing positions for description json
        cameraParams['translation']['positions'] = cam.translationPostions
    
    #generate static camera positions
    elif not cameraParams['translation']['active']:
        for i in range(renderCount):
            cam.translationPostions.append(cam.initLoc)
        #storing positions for description json
        cameraParams['translation']['positions'] = cam.translationPostions

    #generate dynamic camera rotations
    if cameraParams['rotation']['active']:
        randomType = cameraParams['rotation']['random']['method']
        constraint = cameraParams['rotation']['constraint']
        cam.rotationPostions = bt.generateRotations(constraint=         constraint, 
                                                    dynamicObj=         cam.cam, 
                                                    randomType=         randomType, 
                                                    count=              renderCount
                                                    )
        #store positions for description json
        cameraParams['rotation']['positions'] = cam.rotationPostions
    
    #generate static camera rotations
    elif not cameraParams['rotation']['active']:
        for i in range(renderCount):
            cam.rotationPostions.append(cam.initRot)
        #storing positions for description json
        cameraParams['rotation']['positions'] = cam.rotationPostions

    

    '''TODO:

        wed(06/21)
            [X] generate part positions
            [X] move objects on linear traj
            [X] get verticies
                [x] save np mat and check for ground truth object
                [x] check for custom bounding box

        thur(06/22)
            [X] generate postions that obey non convex constraints
            [ ] get camera moving
                [x] follow postions
                [x] return home
                [x] uniform distribution
                [ ] normal distribution
                [x] tracking works
            [ ] get camera rotating
                [ ] add rotation to generated postions
                [ ] uniform
                [ ] normal 
            [X] get lights moving
                [x] follow postions
                [x] return home
            [ ] lighting intensity
                [x] uniform
                [ ] normal
            [X] time remaining estimator

        fri(06/23)
            [X] get camera moving
                [x] normal distribution

            [ ] get camera rotating
                [x] add rotation to generated postions
                [x] uniform
                [ ] normal 
                [x] handle tracking constraint vs free

            [X] lighting intensity
                [x] normal

            [ ] Join descripting dictionaries into single json file for later review
                [x] configure camera parameter dict
                    [x] define all params
                    [x] update all params in render
                [ ] configure classification dict
                    [ ] define all params
                    [ ] update all params in render
                [ ] configure lighting dict
                    [ ] define all params
                    [ ] update all params in render
                [ ] configure domain randomization dict
                    [x] define all params
                    [ ] update all params in render

            [ ] figure out how to search through root dir for datasets that meet certain criteria
        
        mon(06/26)
            - found issue with camera box
                [ ] debug infinite loop issue with normal distribution on camera positions in blenderTools
            [X] built more realistic scene
            [X] added volume constraints for class objects
            [X] render 10 image data set with proper splits
            [ ] add check warning or some sort of logic to handle render count split rounding
            [X] check bounding boxes with custom bounding box dependencies
            [X] fix return to home bug
            [ ] build new adas dataset
            [ ] train new model
             
                '''

    #loop through all classification objects, detirmine positions for each render
    
    for objName in classObjs.classObjects.keys():

        obj = bpy.data.objects[objName]

        for klass in classObjs.classObjects[objName].keys():

            split = classObjs.classObjects[objName][klass]['split']                                 #float

            #calulate how many positions should store for this class
            numOfPositions = int(renderCount * split)           #int


            constraint = classObjs.classObjects[objName][klass]['constraint']

            #if constraint provided and part is dynamic
            if constraint and (objName in bpy.data.collections['dynamicParts'].objects):
                points = bt.generatePositions(constraintObj=    constraint, 
                                              dynamicObj=       obj,        
                                              randomType=       'uniform',  
                                              count=            numOfPositions)
                
                classObjs.classObjects[objName][klass]['positions'] = points 
            


            #identify klassification parameters
            dependency = classObjs.classObjects[objName][klass]['partDependency']                   #object pointer
            
            #if dependency and dependency is dynamic
            if dependency and (dependency.name in bpy.data.collections['dynamicParts'].objects):

                #if a constraint is provided we assume part should move
                dependencyConstraint = classObjs.classObjects[objName][klass]['dependencyConstraint']   #object pointer

                #detirmine positions
                points = bt.generatePositions(constraintObj=    dependencyConstraint,
                                              dynamicObj=       dependency, 
                                              randomType=       'uniform',  
                                              count=            numOfPositions)
         
                
                #add list of points to the dict
                classObjs.classObjects[objName][klass]['dependencyPositions'] = points  


            #debugging
            #debugFile.write(f'index: {objName} \n')
            #debugFile.write(f'klass: {klass} \n')
            #debugFile.write(f'numOfPos: {numOfPositions} \n')
            #debugFile.write(f'positions: {points} \n')
            #debugFile.write('\n')
    #debugFile.close()


    #setCoordinates = [] #array storing projection coordinates of each object in every frame
    setCoordinates = []

    ### MAIN RENDER LOOP ###
    for i in range(renderCount):

        startTime = time.time()

        cam.cam.location = copy.copy(cam.translationPostions[i])

        #NOTE: if cameraParams['tracking']['active'], camera will auto rotate to tracking position first, then we can apply a rotation op after wards
        cam.cam.rotation_euler = copy.copy(cam.rotationPostions[i])


        if domainRandomization['material']['active']:
            for obj in bpy.data.objects:
                if len(obj.material_slots) > 1:
                    bpy.ops.object.select_all(action='DESELECT')

                    obj.select_set(True)
                    #bpy.ops.object.editmode_toggle()

                    #select random material from existin slots
                    idx = random.randint(1, (len(obj.material_slots) - 1))
                    holder = []
                    holder.append(obj.material_slots[idx].material)

                    for j in range(len(obj.material_slots)):
                        if j != idx:
                            holder.append(obj.material_slots[j].material)

                    obj.material_slots[0].material = holder[0]

                    for j in range(1, len(obj.material_slots)):
                        obj.material_slots[j].material = holder[j]

                    bpy.ops.object.select_all(action='DESELECT')
                    
                    #NOTE: there exists bpy.ops.object.material_slot_select() which should make a desired material the active one, however this errors on my version, \
                    #        therefore resorting to reordering loop as insert doesnt work
                     


        for lightName in lights.dynamic.keys():
            light = bpy.data.objects[lightName]
        
            lights.updateIntensity(light, domainRandomization=domainRandomization)
            coord = bt.generatePositions(constraintObj= lights.dynamic[lightName]['constraint'],
                                         dynamicObj= light,
                                         randomType= domainRandomization['lighting']['translation']['random']['method'],
                                         count= 1
                                         )
            bt.updateAbsPosition(light, coord, 0)

        #list to hold image coordinates of each object in the frame thats selected
        frameCoordinates = [] 

        #loop through all objects with classifications
        for object in classObjs.classObjects.keys():
            obj = bpy.data.objects[object]
           
            klassifications = list(classObjs.classObjects[object].keys())   #list of integers
            split = 0

            #loop through each class, detirmine which class is current split
            for klass in klassifications:

                #used to shift indexing from total count 
                idxShift = int(renderCount * split)

                #split value <float [0., 1.]>
                split += classObjs.classObjects[object][klass]['split']     #float
                
                if i < int(renderCount * split): break

            #if main part is dynamic
            objPositions = classObjs.classObjects[object][klass]['positions']
            if objPositions and objPositions != []:
                position = objPositions[i - idxShift]
                bt.updateAbsPosition(obj, [position], 0)
            
         
            #if dependency that will move
            dependency = classObjs.classObjects[object][klass]['partDependency']    #object pointer
            if dependency:
                position = classObjs.classObjects[object][klass]['dependencyPositions'][i - idxShift]   #[x, y, z]
                bt.updateAbsPosition(dependency, [position], 0)
            
           

            
            #Logic to handle custom bboxes for vert projections
            if classObjs.classObjects[object][klass]['customBBox']:
                obj = classObjs.classObjects[object][klass]['customBBox']
                
            else:
                obj = bpy.data.objects[object]

            #project 3D vertecies to 2D image plane
            imageCoordinates = bt.convertVertices(scene, cam.cam, obj, res_x, res_y)

            #append projected vertecies of each object to the image array
            frameCoordinates.append(imageCoordinates)

            #classification label
            label = classObjs.classObjects[object][klass]['label']

            #write instance to csv                                         Ax    Ay    Bx    By    Cx    Cy    Dx    Dy
            instance = [None, str(i) + paths['fileName'] + ".png", label, None, None, None, None, None, None, None, None, cam.cam.location.x, cam.cam.location.y, cam.cam.location.z]
            data.writerow(instance)
            
        #append image array to full render set array
        setCoordinates.append(frameCoordinates)    

        #render
        bpy.ops.render.render(write_still=True)
        bpy.data.images['Render Result'].save_render(paths['renders'] + str(i) + paths['fileName'] + ".png", scene=bpy.context.scene)

        endTime = time.time()
        iterElapsed = endTime - startTime

        _, remainingBar, estimate = bt.timeRemaining(renderCount=renderCount, currentIter=i, iterElapsed=iterElapsed)
        print('')
        print(f'completion: {remainingBar}      {estimate}')

        #update tracking positions
        cameraParams['tracking']['positions'].append(cam.tracker.location)
        cameraParams['pose'].append([cam.cam.location, cam.cam.rotation_euler])

    np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)
    np.save(paths['projectionMat'] + paths['fileName'] + '.npy', setCoordinates)

    #return objects home
    for obj in objs.dynamic.keys():
        part = bpy.data.objects[obj]
        initLoc = objs.dynamic[obj]['initLoc']
        bt.updateAbsPosition(part, [initLoc], 0)
       

    #return Lights Home
    for lightName in lights.dynamic.keys():
        light = bpy.data.objects[lightName]
        light.data.energy = lights.dynamic[lightName]['initIntensity']
        bt.updateAbsPosition(light, [lights.dynamic[lightName]['initLoc']], 0)

    #return camera home
    cam.cam.location = cam.initLoc
    cam.cam.rotation_euler = cam.initRot

    #data descriptions
    description = dict()
    description['cameraParameters'] = cameraParams
    description['domainRandomization'] = domainRandomization

    file.close()

    print("===============================================")





    """
    #intial coordinates
    camInitCart = copy.copy([cam.location.x, cam.location.y, cam.location.z])
    camInitSphere = bt.cart2Sphere([camInitCart[0], camInitCart[1], camInitCart[2]])
    r, theta, phi = camInitSphere[0], camInitSphere[1], camInitSphere[2]
    
    """
   
 
            

#'/home/tuna/Documents/driving/Vision/syntheticData/dataSets/ADAS/'

if __name__ == "__main__":

    renders = dict({
                    'count':    2,
                    })
    
    paths = dict()
    paths['fileName'] =     'testingChange1'
    paths['root'] =         '/media/tuna/Pauls_USBA/adas/' + paths['fileName'] + '/'
    paths['renders'] =      paths['root'] + 'renders/'
    paths['csv'] =          paths['root'] + 'csvFile/'
    paths['jsonFile']=      paths['root'] + 'jsonFile/'
    paths['projectionMat']= paths['root'] + 'projectionMat/'
    paths['descriptionJson']= paths['root'] + 'descriptionJson/'
                  
    
                                                                                        # Parameter Options           Discription
                                                                                        ##########################    #############################################################

    cameraParams = dict({
                        'properties':
                                {
                                'monocular/stereo': 'monocular',                        # [<'monocular'>, <'stereo'>]
                                "baselineDist_mm":  0.,                                 # [<float>] 
                                'focalLength_mm':   25.,                                # [<float>]
                                'sensorWidth_mm':   12.8,                               # [<float>]
                                'sensorHeight_mm':  9.6                                 # [<float>]
                                },

                        'tracking':    
                                {
                                'active':           False,                              # [<True>, <False>]           if set to True, camera will track bpy.data.objects['cameratrackingPoint']
                                'positions':        []                                  # [None]                      will be used to store coordinates of tracking point for description json
                                },                  
                    
                        'translation': 
                                {
                                'active':           False,                               # [<True>, <False>]           if set to True, camera translate within constraint **must have a constraint**
                                'random':          
                                    { 
                                    'method':       'uniform',                           # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                    'mean':         'initLoc',                          # [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                                    'sigma':        1/3                                 # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                    },
                                },

                        'rotation':    
                                {
                                'active':           False,                               # [<True>, <False>]           if set to True, camera will include rotation in randomization
                                'constraint':       [                                   #                             **only used for normal distribution**
                                                    (-np.pi/6, np.pi/6),                # [(<float>, <float>)]        theta limits 
                                                    (-np.pi/10, np.pi/10),              # [(<float>, <float>)]        phi limits
                                                    (0., 0.)                            # [(<float>, <float>)]        psi limits
                                                    ],               
                                'random':          
                                        { 
                                        'method':   'uniform',                          # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                        'mean':     'initLoc',                          # [<'intiLoc'>]               centered at intial rotation, NOTE: if tracking is active, camera rotations will auto over ride the initLoc mean and will be applied after tracking rotation
                                        'sigma':    1/3                                 # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                        },
                                },
                        'pose':                     []                                  # [[<floats>], [<floats>]]    [[x, y, z], [theta, phi, psi]]    will be used to store pose information for description json
                        })


    
                                                                                        # Parameter Options #         Discription
                                                                                        ##########################    #############################################################                                                                            
    domainRandomization = dict({
                                'lighting':                                             # '''NOT IMPLENTED'''         Control lighiting in scene
                                        {
                                        'active':               True,                   # [<True>, <False>]
                                        'translation':
                                                {
                                                'random':    
                                                    {
                                                    'method':   'uniform',              # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                                    'mean':     None,                   # [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                                                    'sigma':    1/3                     # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                                    }
                                                },
                                        'intensity':
                                                {
                                                'random':    
                                                    {
                                                    'method':   'normal',               # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                                    'mean':     'initLoc',              # [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                                                    'sigma':    1/3                     # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                                    },
                                                }
                                        },

                                'material':                                             # '''NOT IMPLEMENTED'''       Control material randomization of objects
                                        {
                                        'active':           True,                       # [<True>, <False>]  
                                        'assetRootDir':     None                        # [<None>, <Path_to_assets>]  None: pulls from default environment assets, or supply path to custom asset folder  
                                        },                  

                                'color':                                                # '''NOT IMPLEMENTED'''
                                        {
                                        'active':           True,                       # [<True>, <False>] 
                                        'HSL_range':        False,                      # [<[[H_min,H_max],[S_min,S_max],[L_min,L_max]]>, <False>]   if not false, HSL values will be random uniform selected from provided ranges
                                        'colorDir':         None                        # [<Path_to_color.txt>]
                                        },

                                'environment':                                          # '''NOT IMPLEMENTED'''
                                        {
                                        'dust':             False,
                                        'abrasion':         False
                                        }               
                            })

    generalinfo = dict({
                        'source':               "synthetic-gen",
                        'part':                 "ADAS-ECU",

                        'path_to_blendFile':    None,

                        'renderMethod':         'cycles',
                        'resolution_px':        760,
                        'resolution_py':        556,

                        'imageIDs':             []                                      #                               list of image names
                            
    })


    main(renderInfo=            renders,
         cameraParams=          cameraParams,
         domainRandomization=   domainRandomization,
         paths=                 paths)
    
    
    