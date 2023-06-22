import bpy
from bpy_extras.object_utils import world_to_camera_view
import csv
import numpy as np
import copy
import time
import random
import sys

import bmesh
import mathutils

sys.path.append("/home/tuna/Documents/driving/Vision/syntheticData/")
from utils import blenderTools2 as bt


''' This script must be run from within blender scripting environment

    Current as of 06/22/2023
        Blender:    3.5
        python:     3.7
        
    
        TODO: 
            [X] figure out how to set object contraints easily
            [ ] verify that all refactor works with simple dataset
            [X] add compute time remaining to terminal output
            [X] set up domain randomization params, set up collections for each object
            [ ] figure out how to pull from material library through bpy
            [ ] add a key stroke break command
            [ ] add render start warnings if things are missing ( eg, if Lighting DR is true but no lighting BBox active etc)
          
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
            self.dynamic[light.name]['constraint'] = light.data['constraint']
            self.dynamic[light.name]['initIntensity'] = copy.copy(light.data.energy)
            
            #check if intensity specified
            try: self.dynamic[light.name]['intensityRange'] = light.data['intensityRange'] #[min, max]
            except: self.dynamic[light.name]['intensityRange'] = None

        for light in bpy.data.collections['staticLights'].objects:

            if light.instance_type != 'LIGHT': pass
            self.static.append(light)

    def updateIntensity(self, light, domainRandomization):

        #break if light is not in dynamic collection
        if light.name not in self.dynamic.keys():
            return
        
        #break if light does not have intensity range set
        if self.dynamic[light.name]['intensityRange'] == None:
            return
        

        dr = domainRandomization['lighting']['intensity']['random']

        if dr['method'] == 'normal':
            newIntensity = np.random.Generator.normal(loc=self.dynamic[light.name]['initIntensity'], scale=dr['sigma'])

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
        self.translationPostions = None
        self.rotationPostions = None

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
            check = 0 
            try:
                obj.data[f'1.classLabel']
                self.classObjects[obj.name] = dict()

                print(f'found a classification for {obj.name}')

                while True:
                    try:

                        label = obj.data[f'{count}.classLabel']
                        check = 1
                        split = obj.data[f'{count}.split']      #float
                        
                        check = 2
                        constraintID = obj.data[f'{count}.constraint']              #<string> should be the name of an object in the scene

                        if constraintID != '<objectID>': constraintObj = bpy.data.objects[constraintID]     #if the user defined this, look for that object and save the pointer
                        else: constraintObj = None
                        check = 3

                        customBBoxID =  obj.data[f'{count}.customBBox']

                        if customBBoxID != '<objectID>': customBBoxObj = bpy.data.objects[customBBoxID]
                        else: customBBoxObj = None
                        check = 4
                        
                        partDependencyID = obj.data[f'{count}.partDependency']

                        if partDependencyID != '<objectID>': partDependencyObj = bpy.data.objects[partDependencyID]
                        else: partDependencyObj = None
                        check = 5

                        dependencyConstraintID = obj.data[f'{count}.dependencyConstraint']

                        if dependencyConstraintID != '<Path, Plane, or Volume ID>': dependencyConstraintObj = bpy.data.objects[dependencyConstraintID]
                        else: dependencyConstraintObj = None
                        check = 6
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
                        check = 7
                       
                        count += 1
                    
                    except: 
                        if check != 7: 
                            print('failed to build proper classification dict')
                            print(f'failed on {check}')

                        break

            except: pass            


class objects():

    def __init__(self):

        self.static = []
        self.dynamic = dict()
        
        for object in bpy.data.collections['dynamicParts'].objects:

            self.dynamic[object.name] = {
                                            'initLoc':      object.location,
                                            'initRot':      object.rotation_euler,
                                            'material':     object.data.materials
                                        }
            

def main(renderInfo, cameraParams, domainRandomization, paths):
    print('')
    
    #debugging
    file = open("/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt", 'w')

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

    #turn tracking on
    if cameraParams['tracking']['active']: 
        cam.toggleTracking()

    #generate camera trasnlational postions
    if cameraParams['translation']['active']:
            randomType = cameraParams['translation']['random']['method']
            cam.translationPostions = bt.generatePositions(constraintObj=   cam.constraint, 
                                                            dynamicObj=     cam.cam, 
                                                            randomType=     randomType, 
                                                            count=          renderCount
                                                            )

    file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')

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
            [ ] get camera moving
                [ ] normal distribution
            [ ] get camera rotating
                [ ] add rotation to generated postions
                [ ] uniform
                [ ] normal 
            [ ] lighting intensity
                [ ] normal
             
                '''

    #loop through all classification objects, detirmine positions for each render
    for objName in classObjs.classObjects.keys():

        for idx, klass in enumerate(classObjs.classObjects[objName].keys()):

            #identify klassification parameters
            dependencyConstraint = classObjs.classObjects[objName][klass]['dependencyConstraint']   #object pointer
            dependency = classObjs.classObjects[objName][klass]['partDependency']                   #object pointer
            split = classObjs.classObjects[objName][klass]['split']                                 #float

            #calulate how many positions should store for this class
            numOfPositions = int(renderCount * split)           #int

            #detirmine positions
            points = bt.generatePositions(constraintObj=   dependencyConstraint,
                                           dynamicObj=      dependency, 
                                           randomType=      'uniform',  
                                           count=           numOfPositions)

            #add list of points to the dict
            classObjs.classObjects[objName][klass]['dependencyPositions'] = points  

            #debugging
            file.write(f'index: {objName} \n')
            file.write(f'klass: {klass} \n')
            file.write(f'numOfPos: {numOfPositions} \n')
            file.write(f'positions: {points} \n')
            file.write('\n')
    file.close()


    setCoordinates = [] #array storing projection coordinates of each object in every frame


    for i in range(renderCount):

        startTime = time.time()

        cam.cam.location = cam.translationPostions[i]
        #TODO: add cam rotations



        for lightName in lights.dynamic.keys():
            light = bpy.data.objects[lightName]
        
            lights.updateIntensity(light, domainRandomization=domainRandomization)
            coord = bt.generatePositions(constraintObj= lights.dynamic[lightName]['constraint'],
                                         dynamicObj= light,
                                         randomType= domainRandomization['lighting']['translation']['random']['method'],
                                         count=1
                                         )
            bt.updateAbsPosition(light, coord, 0)

        #list to hold image coordinates of each object in the frame thats selected
        frameCoordinates = [] 

        #loop through all objects with classifications
        for object in classObjs.classObjects.keys():

            klassifications = list(classObjs.classObjects[object].keys())   #list of strings
            split = 0

            #loop through each class, detirmine which class is current split
            for klass in klassifications:

                #used to shift indexing from total count 
                idxShift = int(renderCount * split)

                #split value <float [0., 1.]>
                split += classObjs.classObjects[object][klass]['split']     #float
                
                if i < int(renderCount * split): break
            
            #object that will move
            dependency = classObjs.classObjects[object][klass]['partDependency']    #object pointer

            #new position
            position = classObjs.classObjects[object][klass]['dependencyPositions'][i - idxShift]   #[x, y, z]

            #update position of the object
            bt.updateAbsPosition(dependency, [position], 0)
            
            #Logic to handle custom bboxes for vert projections
            if classObjs.classObjects[object][klass]['customBBox']:
                obj = classObjs.classObjects[object][klass]['customBBox']
                #print('found custom bbox')
            else:
                obj = bpy.data.objects[object]
                #print('no custom bbox detected')

            #convert vertecies to image plane
            imageCoordinates = bt.convertVertices(scene, cam.cam, obj, res_x, res_y)

            #append projected vertecies of each object to the image array
            frameCoordinates.append(imageCoordinates)
            
        #append image array to full render set array
        setCoordinates.append(frameCoordinates)    

        #render
        bpy.ops.render.render(write_still=True)
        bpy.data.images['Render Result'].save_render(paths['renders'] + paths['fileName'] + str(i) + ".png", scene=bpy.context.scene)

        endTime = time.time()
        iterElapsed = endTime - startTime

        _, remainingBar, estimate = bt.timeRemaining(renderCount=renderCount, currentIter=i, iterElapsed=iterElapsed)
        print('')
        print(f'{estimate}      completion: {remainingBar}')

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

    bt.updateAbsPosition(cam.cam, [cam.initLoc], 0)


    print("===============================================")





    """
    #intial coordinates
    camInitCart = copy.copy([cam.location.x, cam.location.y, cam.location.z])
    camInitSphere = bt.cart2Sphere([camInitCart[0], camInitCart[1], camInitCart[2]])
    r, theta, phi = camInitSphere[0], camInitSphere[1], camInitSphere[2]

    camBoundingCubeOuter = bpy.data.objects['CamTranslationBoundingCubeOuter']
    camBoundsouter = bt.getCartesianBounds(camBoundingCubeOuter)
    camTransLimits = [abs(camBoundsouter[0][1] - camBoundsouter[0][0]),
                      abs(camBoundsouter[1][1] - camBoundsouter[1][0]),
                      abs(camBoundsouter[2][1] - camBoundsouter[2][0])]
    #generate normal distribution of camera coords around intial location
    camPositions = [[], [], [], [], []] #[[x], [y], [z], [theta], [phi]]
    camPositions[0] = np.random.default_rng().normal(loc=0, scale=camTransLimits[0]/4, size=renderCount)
    camPositions[1] = np.random.default_rng().normal(loc=0, scale=camTransLimits[1]/4, size=renderCount)
    camPositions[2] = np.random.default_rng().normal(loc=0, scale=camTransLimits[2]/4, size=renderCount)
    camPositions[3] = np.random.default_rng().normal(loc=0, scale=cameraRotLimits[0]/4, size=renderCount)
    camPositions[4] = np.random.default_rng().normal(loc=0, scale=cameraRotLimits[1]/4, size=renderCount)
    #restrain to limits
    camPositions[0] = np.clip(camPositions[0], -camTransLimits[0],  camTransLimits[0])
    camPositions[1] = np.clip(camPositions[1], -camTransLimits[1],  camTransLimits[1])
    camPositions[2] = np.clip(camPositions[2], -camTransLimits[2],  camTransLimits[2])
    camPositions[3] = np.clip(camPositions[0], -cameraRotLimits[0], cameraRotLimits[0])
    camPositions[4] = np.clip(camPositions[1], -cameraRotLimits[1], cameraRotLimits[1])
    
    file = open(csvPath + fileName + ".csv", "w")
    data = csv.writer(file)
    #top row column titles
    labelID = ["use", "fileName", "classification","xMin", "yMin", None, None, "xMax", "yMax", None, None]
    data.writerow(labelID)

    setCoordinates = [] #array storing projection coordinates of each object in every frame

    for i in range(0, renderCount):
        
        bpy.ops.render.render(write_still=True)
        
        #update projected coordinates array
        frameArray = [] #list to hold image coordinates of each object in the frame thats selected
        classification = []
        
        tempFileName = fileName    

        for j in range(len(obj)):

            imageCoordinates = bt.convertVertices(scene, cam, obj[j], res_x, res_y)
            frameArray.append(imageCoordinates)
        
            if (obj[j].location == initLoc[j]) and (obj[j].rotation_euler == initRot[j]): classification.append(str(j+1)+'OK')
            else: classification.append(str(j+1) + 'NO')

        for j in range(len(obj)):
            tempFileName = tempFileName + f"_{classification[j]}"
           

        for j in range(len(obj)):

            instance = [None, str(i) + tempFileName + ".png", classification[j], None, None, None, None, None, None, None, None]
            data.writerow(instance)

        render_path = renderPath + str(i) + tempFileName + ".png"
        bpy.data.images['Render Result'].save_render(render_path, scene=bpy.context.scene)
        #write instance to csv
        #

        
        setCoordinates.append(frameArray)"""
            


if __name__ == "__main__":



    renders = dict({
                    'count':    10,
                    })
    
    paths = dict()
    paths['fileName'] =     'synthGenT1'
    paths['root'] =         '/home/tuna/Documents/driving/Vision/syntheticData/dataSets/RCM/' + paths['fileName'] + '/'
    paths['renders'] =      paths['root'] + 'renders/'
    paths['csv'] =          paths['root'] + 'csvFile/'
    paths['jsonFile']=      paths['root'] + 'jsonFile/'
    paths['projectionMat']= paths['root'] + 'projectionMat/'
                  
    
                                                                                        # Parameter Options           Discription
                                                                                        ##########################    #############################################################

    cameraParams = dict({
                        'tracking':    
                                {
                                'active':          False                                # [<True>, <False>]           if set to True, camera will track bpy.data.objects['cameratrackingPoint']
                                },                  
                    
                        'translation': 
                                {
                                'active':          True,
                                'random':          
                                    { 
                                    'method':  'uniform',                               # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                    'mean':    'initLoc',                               # [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                                    'sigma':   1/3                                      # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                    }
                                },

                        'rotation':    
                                {
                                'active':          False,                               # [<True>, <False>]           if set to True, camera will include rotation in randomization
                                'constraint':      [np.pi/6, np.pi/10, 0],              # [<theta>, <phi>, <psi>]     **only used for normal distribution**
                                'random':          
                                        { 
                                        'method':  'normal',                            # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                        'mean':    'initLoc',                           # [<'intiLoc'>]               centered at intial rotation **only used for noraml distribution**
                                        'sigma':   1/3                                  # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                        }
                                }
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
                                                    'method':   'uniform',              # [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                                                    'mean':     None,                   # [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                                                    'sigma':    1/3                     # [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**
                                                    },
                                                }
                                        },

                                'material':                                             # '''NOT IMPLEMENTED'''       Control material randomization of objects
                                        {
                                        'active':           True,                       # [<True>, <False>]  
                                        'assetDir':         None                        # [<None>, <Path_to_assets>]  None: pulls from default environment assets, or supply path to custom asset folder  
                                        },                  

                                'color':                                                # '''NOT IMPLEMENTED'''
                                        {
                                        'active':           True,                       # [<True>, <False>] 
                                        'HSL_range':        False,                      # [<[[H_min,H_max],[S_min,S_max],[L_min,L_max]]>, <False>]   if not false, HSL values will be random uniform sleected from provided ranges
                                        'colorDir':         None                        # [<Path_to_color.txt>]
                                        },

                                'environment':                                          # '''NOT IMPLEMENTED'''
                                        {
                                        'dust':             True,
                                        'abrasion':         False
                                        }               
                            })


    main(renderInfo=            renders,
         cameraParams=          cameraParams,
         domainRandomization=   domainRandomization,
         paths=                 paths)
    
    
    