import bpy
from bpy_extras.object_utils import world_to_camera_view
import csv
import numpy as np
import copy
import time
import random
import bmesh
import mathutils

def convertVertices(scene, cam, obj, resolutionX, resolutionY):
    
    ''' returns a list of object vertex coordinates projected onto image plane
        output = [[x, y, depthToCamera]] '''
    
    projectedVertices = []

    for vertex in obj.data.vertices:
        worldCoords = obj.matrix_world @ vertex.co
        coords_2d = world_to_camera_view(scene, cam, worldCoords)   #built in matrix multiplication func
        x = coords_2d[0]
        y = coords_2d[1]
        depth = round(coords_2d[2], 3) #clip unneccessary float precision
        projectedVertices.append([int(resolutionX*x), int(resolutionY - resolutionY*y), depth]) #use reolution to redifine coordinates

    return projectedVertices

def updatePosition(obj, trajectory, timeStep):

    ''' adds velocity to position '''

    obj.location.x += trajectory[timeStep][0]
    obj.location.y += trajectory[timeStep][1]
    obj.location.z += trajectory[timeStep][2]

def updateAbsPosition(obj, absTrajectory, timeStep):
    
    ''' updates absolute coordinates 
    
        PARAMS:
            obj:            Blender object
            absTrajectory:  [[x1, y1, z1], [x2 ...]] coordinates
            timeStep:       Default index = 0, can pass as timestep to pull cordinates from a trajectory instead of single position'''

    obj.location.x = absTrajectory[timeStep][0]
    obj.location.y = absTrajectory[timeStep][1]
    obj.location.z = absTrajectory[timeStep][2]

def rotate(obj, trajectory, timeStep):

    obj.rotation_euler[0] += trajectory[timeStep][0]
    obj.rotation_euler[1] += trajectory[timeStep][1]
    obj.rotation_euler[2] += trajectory[timeStep][2]
    
def enumeratePath(path, i):

    ''' introduces itterable numbers into file path '''

    fileName = path.split('.')
    return fileName[0] + str(i) + '.' + fileName[-1]

def sphere2Cart(sphere):

    '''converts spherical coordinates [r, theta, phi] into cartesian [x, y, z] '''

    r, theta, phi = sphere[0], sphere[1], sphere[2]
    x = r*np.sin(phi)*np.cos(theta)
    y = r*np.sin(phi)*np.sin(theta)
    z = r*np.cos(phi)

    return [x, y, z]

def cart2Sphere(cart):

    ''' converts cartesian coords [x, y, z] into spherical coords [r, theta, phi] '''

    x, y, z = cart[0], cart[1], cart[2]
    r = np.sqrt(x**2 + y**2 + z**2)
    theta = np.arctan(y/x)
    #handle limit exception of arctan
    if x < 0:
        theta += np.pi
    phi = np.arccos(z/r)
    return [r, theta, phi]

def getCartesianBounds(obj):

    '''returns cartesian bounding cube constraint coordinates from argument object
        Assumes bounding rectangular prizm
        struct: [[minX, maxX], [minY, maxY], [minZ, maxZ]]
        '''
    #bounding_box = [obj.matrix_world]# @ vertex.co for vertex in obj.bound_box]

    bounding_box = []
    #solve for world coordinates of cube vertices
    for vertex in obj.data.vertices:
        worldCoords = obj.matrix_world @ vertex.co
        bounding_box.append(worldCoords)

    #extract x, y, z
    xMin, xMax = bounding_box[0][0], bounding_box[7][0]
    yMin, yMax = bounding_box[0][1], bounding_box[7][1]
    zMin, zMax = bounding_box[0][2], bounding_box[7][2]

    return [[xMin, xMax],[yMin, yMax], [zMin, zMax]]


def getRandomCarts(outerConstraint, innerConstraint=None, randomType='Uniform', NormalCenter = 'center', sigma = None):
    
    '''
    Params:
        outerConstraint:    [[x0, x1], [y0,y1], [z0,z1]]
        randomType:         'Uniform', 'Normal'
        NormalCenter:       'Lower', 'Center', 'Upper'

    Returns [x, y, z] obeying constraints, Assumes rectangular prizm constraints'''
    
    if randomType == 'Uniform':
        x = random.uniform(outerConstraint[0][0], outerConstraint[0][1])
        y = random.uniform(outerConstraint[1][0], outerConstraint[1][1])
        z = random.uniform(outerConstraint[2][0], outerConstraint[2][1])
    
        return [x, y, z]
    
    elif randomType == 'Normal':
        if NormalCenter == 'Lower': mu = [outerConstraint[0][0], outerConstraint[1][0], outerConstraint[2][0]]
        elif NormalCenter == 'Upper':mu = [outerConstraint[0][1], outerConstraint[1][1], outerConstraint[2][1]]
        else: mu = [(outerConstraint[0][0] + outerConstraint[0][1])/2,
                    (outerConstraint[1][0] + outerConstraint[1][1])/2, 
                    (outerConstraint[2][0] + outerConstraint[2][1])/2]
            
        if sigma == None:    
            sigma = [abs(outerConstraint[0][0] - outerConstraint[0][1])/4,
                    abs(outerConstraint[1][0] - outerConstraint[1][1])/4,
                    abs(outerConstraint[2][0] - outerConstraint[2][1])/4,]
          
        x = abs(random.normalvariate(mu[0], sigma[0]))
        y = abs(random.normalvariate(mu[1], sigma[1]))
        z = abs(random.normalvariate(mu[2], sigma[2]))

        #constrain to limits (Normal variate sometimes produces large variations, uniform random does not have this problem)
        x = np.clip(x, outerConstraint[0][0], outerConstraint[0][1])
        y = np.clip(y, outerConstraint[1][0], outerConstraint[1][1])
        z = np.clip(z, outerConstraint[2][0], outerConstraint[2][1])

        return [x, y, z]


def rcmUpdate(obj, tLimits, rLimits, initLoc, initRot):

    '''custom update function that handles rotation of the clip on the component'''
    
    file = open("/home/tuna/Documents/driving/Vision/syntheticData/dataSets/RCM/singleClipB.txt", 'w')

    rcmBody = obj[1]
    #rcmBody = obj[0]
    rcmClip = obj[0]

    newPos = getRandomCarts(tLimits, randomType='Normal', NormalCenter='Lower')
    
    

    updateAbsPosition(rcmBody, [[initLoc[1][0] + newPos[0], initLoc[1][1] + newPos[1], initLoc[1][2] + newPos[2]]], 0)
    #updateAbsPosition(rcmBody, [[initLoc[0][0] + newPos[0], initLoc[0][1] + newPos[1], initLoc[0][2] + newPos[2]]], 0)

    file.write(str(rcmBody) + "\n")
    file.write(f'initLoc[0][0]: {initLoc[0][0]}, newPos[0]:{newPos[0]} \n')

    dx = abs(abs(initLoc[0][0]) - abs(newPos[0]))
    clipAngle = 4 * newPos[0]
    if clipAngle > rotationLimits[0][1]: clipAngle = rotationLimits[0][1]
    file.write("\n")
    file.write(f'dx: {dx} \n clipAngle: {clipAngle} \n')
    file.write("\n")
    
    rcmClip.rotation_euler[0] = initRot[0][0] + clipAngle
    rcmClip.rotation_euler[1] = initRot[0][1] 
    rcmClip.rotation_euler[2] = initRot[0][2] 

    #file.write(str(rcmClip))
    file.close()

    return


def curveLimits(obj):

    '''Take a curve object, convert to mesh and return limit verticies converted to world frame'''

    limits = []

    bpy.ops.object.convert(target='MESH', keep_original=True, merge_customdata=True, angle=1.22173, thickness=5, seams=False, faces=True, offset=0.01)

    meshCurve = bpy.context.selected_objects[0]

    curveCoords = [meshCurve.data.vertices[0].co, meshCurve.data.vertices[-1].co]
    curveWorldMat = meshCurve.matrix_world

    limits.append(curveWorldMat @ curveCoords[0])
    limits.append(curveWorldMat @ curveCoords[1])

    bpy.ops.object.select_all(action='DESELECT')
    meshCurve.select_set(True)
    bpy.ops.object.delete()

    return limits


def planarLimits(obj):

    '''Take a planar object, return a list of vertices at limit of object converted to world coordinates'''

    limits = []

    for vert in obj.data.vertices:
        coord = vert.co
        limits.append(obj.matrix_world @ coord)

    return limits
    
def volumeLimits(obj):

    '''Take a volume object, return a list of vertices at limit of object converted to world coordinates'''

    ### Redundant placeholder ###

    limits = []

    for vert in obj.data.vertices:
        coord = vert.co
        limits.append(obj.matrix_world @ coord)

    return limits



def callBack():
    file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')
    file.write('hello')
    file.close()
    return 

def constraintLimits(constraint):

    limits = []
    
    file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')
    file.write('in func\n')
    file.write(f'constraint:{constraint} \n')
    file.write(f'constraint:{constraint.type} \n')
    file.write('and1 \n')

    if constraint.type == 'CURVE':
        file.write('found a curve')
        bpy.ops.object.convert(target='MESH', keep_original=True, merge_customdata=True, angle=1.22173, thickness=5, seams=False, faces=True, offset=0.01)

        meshCurve = bpy.context.selected_objects[0]

        curveCoords = [meshCurve.data.vertices[0].co, meshCurve.data.vertices[-1].co]
        curveWorldMat = meshCurve.matrix_world

        limits.append(curveWorldMat @ curveCoords[0])
        limits.append(curveWorldMat @ curveCoords[1])

        bpy.ops.object.select_all(action='DESELECT')
        meshCurve.select_set(True)
        bpy.ops.object.delete()

    #planar object mesh
    elif (constraint.type == 'MESH') and (len(constraint.data.vertices) == 4):
        file.write('found a mesh plane')
        for vert in constraint.data.vertices:
            coord = vert.co
            limits.append(constraint.matrix_world @ coord)

    #Volume object mesh
    else:
        file.write('found a mesh vol')
        for vert in constraint.data.vertices:
            coord = vert.co
            limits.append(constraint.matrix_world @ coord)

    file.close()

    return limits





def countClasses():
    
    '''returns int number of objects with "class" at the start of name'''

    ## DEPRECATED ###
    
    classes = []
    for obj in bpy.data.objects[:]:
        s = obj.name.split('.')
        if s[0] == 'class': classes.append(obj)
        
    return len(classes)


def visualizeDataStruct(dataObject):
    
    '''helper for writing txt file to visualize data struct, these get complex in blender'''

    file = open('/home/tuna/Documents/driving/Vision/syntheticData/bpyTest.txt', 'w')

    file.write(f'object ID: {dataObject} \n \n')

    for item in dir(dataObject):
        file.write(f'\t attribute: {item} \n')

    file.close()
    return 


def generatePositions(constraintObj, dynamicObj, randomType, count):

    """ This function is designed to generate position coordinates that respect constraint boundaries.

    PARAMS:

        constraintObj:  <object pointer>        that will be used as constraint
        dynamicObj:     <object pointer>        to the part for which we want to move, this is only used to identify intial location
        randomType:     <'uniform', 'normal'>   Logic for point distribution, <normal> will use dynamic object init location as mean
        count:          <int>                   Number of required positions

    constraint types:

        'CURVE' constraints: TBD
                - should lerp along curves using the type of curve, ie bezier with control points

        'PLANE' constraints: TBD
                - should utilize formula for the plane, then ray cast away from origin to detirmine bound success

        'MESH'  constraints: 
                - function uses ray casting to detirmine coordinate positions within a volume
                - this is not perfect, right now i cast rays using a unit vector in the direction from the origin to the potential point
                  for non-convex geometries there is a posibility that the ray is still intercepted on the part even though the point is 
                  outside of the constraint limits. for now this is good enough though to move forward, but should return to this in the 
                  future to improve fucntionality """
    
    goodPoints = []

    if constraintObj.type == 'CURVE':

        potentialPositions = []
        
        bpy.ops.object.select_all(action='DESELECT')
        constraintObj.select_set(True)

        mCurve = constraintObj.to_mesh(preserve_all_data_layers=True)

        #build list of all vertex positions in world frame
        for vert in mCurve.vertices:
            coord = vert.co
            potentialPositions.append(constraintObj.matrix_world @ coord)

        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.delete()
    
        #generate a random list if indicies to pull from 
        selectionList = np.random.randint(low= 0, high=len(potentialPositions), size=count)

        #build list of actual postions, this may have duplicates from the postential position list of the desired numbber of positions
        # is greater than the number of vertecies that are require to define the curve mesh
        for selection in selectionList:
            goodPoints.append(potentialPositions[selection])

        return goodPoints
            

    if constraintObj.type == 'PLANE':
        return

    if constraintObj.type == 'MESH':

        #dependency graph, needed for ray casting
        depsgraph = bpy.context.evaluated_depsgraph_get()

        #ensure mesh for vertecies
        mesh = constraintObj.to_mesh(preserve_all_data_layers=True)

        #deselect all
        bpy.ops.object.select_all(action='DESELECT')

        #select constraint object
        constraintObj.select_set(True)

        #save initial object origin location
        constraintInitLoc = constraintObj.location
        bpy.context.scene.cursor.location = constraintInitLoc
        
        #set origin to center of mass
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
        worldOrigin = constraintObj.location

        #reset origin to original position
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        #store init location of moving object for 'normal' distribution
        dynamicInitLoc = dynamicObj.location

        #possible ranges without obeying geometry constraint yet
        min_x, max_x = min(v.co.x for v in mesh.vertices), max(v.co.x for v in mesh.vertices)
        min_y, max_y = min(v.co.y for v in mesh.vertices), max(v.co.y for v in mesh.vertices)
        min_z, max_z = min(v.co.z for v in mesh.vertices), max(v.co.z for v in mesh.vertices)
        
        # collect good points
        attempt = 0
        while len(goodPoints) < count:

            if randomType == 'uniform':

                # ray cast requires point type to be a tuple
                point = (
                        random.uniform(min_x, max_x),
                        random.uniform(min_y, max_y),
                        random.uniform(min_z, max_z)
                        )
                
            if randomType == 'normal':

                # ray cast requires point type to be a tuple
                point = (
                        random.normalvariate(dynamicInitLoc[0], abs(max_x - min_x)/3),
                        random.normalvariate(dynamicInitLoc[1], abs(max_y - min_y)/3),
                        random.normalvariate(dynamicInitLoc[2], abs(max_z - min_z)/3)
                        )
                
                #clamp to constraint limits
                #TODO: add decay term to ensure these terminate
                while (point[0] < min_x) or (point[0] > max_x): point[0] = random.normalvariate(dynamicInitLoc[0], abs(max_x - min_x)/3)
                while (point[1] < min_y) or (point[1] > max_y): point[1] = random.normalvariate(dynamicInitLoc[1], abs(max_y - min_y)/3)
                while (point[2] < min_z) or (point[2] > max_z): point[2] = random.normalvariate(dynamicInitLoc[2], abs(max_z - min_z)/3)
                
            #must convert tuple to vector
            pointVec = mathutils.Vector(point)

            #convert local coordinate to world frame
            worldPoint = constraintObj.matrix_world @ pointVec
           
            #vector from center of mass to new random point
            origin2Point = worldPoint - pointVec
            mag = np.sqrt(origin2Point[0]**2 + origin2Point[1]**2 + origin2Point[2]**2)
            unitVec = (origin2Point[0]/mag, origin2Point[1]/mag, origin2Point[2]/mag)
           
            #cast ray, if ray hits a face of the object, poly_idx will be positive, else -1
            _, _, _, poly_idx = constraintObj.evaluated_get(depsgraph).ray_cast(point, unitVec)

            #store good points
            if poly_idx != -1:
                goodPoints.append(worldPoint)

            #TODO: update this to handle use casses where more than 500 points are desired
            if attempt > 500:
                break

            attempt += 1

        return goodPoints
    

def timeRemaining(renderCount, currentIter, iterElapsed):

    ''' nice way to check in on progress for long render tasks '''

    remainingBar = '['
    avg = 0

    percentComplete = int((currentIter/renderCount) * 10)

    for i in range(percentComplete):
        remainingBar = remainingBar + '#'
    
    for i in range(10-percentComplete):
        remainingBar = remainingBar + ' '
    
    remainingBar = remainingBar + ']'

    totalSeconds = int(iterElapsed * (renderCount - currentIter))
    minutesRemain = round(totalSeconds/60, 2)

    estimate = f'remaining minutes: {minutesRemain}'

    return avg, remainingBar, estimate