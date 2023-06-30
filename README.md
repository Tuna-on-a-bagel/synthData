# Synthetic Data generation overview

## Requirements:
* Blender version:    3.6.0  
* Python Version:     3.9.13  
* Ubuntu Version:     20.04  

This package is designed to collaborate with blender files in order to generate synthetic images for training AI vision models. The current implementation is able to provide ground truth or custom bounding boxes for object detection. There are several utility files associated with this package:
  * spawDirs.py:          Used to create consistent directory structures across all datasets
  * setupEnvironment.py   Used to register custom classes to aid in synthetic data generation from blender UI
  * synthGen.py:          Handles .blend file and generation parameters, renders and stores images, initial csv, and vertex projectoin array
  * buildDataSet.py:      Used to handle unique variations of csvv/jsonl file creation, also handles identifying image coordinates for bounding boxes
  * blenderTools.py:      Stores functions called from synthGen.py
  

The majority of the work that will be done is through the blender UI. A tutorial video for working with this specific package can be found
at: _LinkToVideo_

All of these modules utilize the blender python api bpy. Documentation for bpy can be found here: https://docs.blender.org/api/current/index.html
NOTE: this documentation is fairly weak, you may encounter many problems when calling certain functions. There have been many changes made between bpy 2.8 and 3.5, but the 3.5 documentation is lagging behind.

## spawnDirs.py usage:

This file must be run prior to any other process. This will generate a consistent directory structure between all data sets that might prevent issues later on when locating files. The general structure for each datset will look like:

    root directory/
    |-- <fileName>/
        |--  csvFile/
        |    |--   <fileName>.csv                   csv file storing excess information including both BBox coordinates and camera locations etc
        |    |--   <fileName>_gcp.csv               csv file that removes excess information, structured for gcp usage
        |   
        |--  descriptionJson/
        |    |--   <fileName>_description.json      json used to store excess scene information for building/extracting super/sub sets 
        |
        |--  jsonFile/
        |    |--   <fileName>.jsonl                 jsonl for gcp usage
        |
        |--  projectionMat/
        |    |--   <fileName>.npy                   numpy array storing all vertext projections to image plane of objects with classification
        |                                           association in blender file
        |--  renders/
        |    |--   0<fileName>.png
        |    |--   1<fileName>.png
        |    |--   ...
        |    |--   n<fileName>.png

## setupEnvironment.py usage:

This file will register the custom synthetic data tools into the blender UI. From blender UI, navigate to `scripting`, then load in this file and run. From the main 3D viewport area, you will see a new tab appear named `'Synth Tools'` under the orientation axis in the top right corner. See the tutorial video for an overview on how these tools can be used.

![blender_synthTools](https://github.com/Tuna-on-a-bagel/synthData/assets/51982197/dbce332d-cd8e-4476-bc00-8d582e267cba)

## synthGen1.py usage:
        
This file handles the majority of the generation procedures. From blender UI, navigate to `scripting`, then load in this file. Scroll to the bottom of the file where you will find several dictionaries containing parameters to control the rendering. Again, the majority of the tools for making unique modifcations are found within the blender UI, and you should see the tutorial video link to learn how to manipulate these. However, the dictionaries in this document can be used to set global modifications and control things such as render count, domain randomization, random distribution types, Camera parameters, and general scene info such as CAD model identifiers etc.  

When you have set every parameter to your needs, running this script will start the process. The render engine will use whatever device is selected through `>edit, preferences, >system, >cycles render device`, you should verify that the correct GPU device is enabled before running.

### Built in methods:

camera class:

```python
camera.toggleTracking()
```
Used to turn on and off the camera tracking constraint. When turned on, and environment that was built from `basicEnvironment.blend` will have the camera orient itself such that the Z axis is up and it's center is aligned with `bpy.data.objects['camera.focalPt']`. You can make the camera.focalPt a static or dynamic object.

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `None` |  |  | `None` |  |  |

 -----------

lighting class:

```python
lights.updateIntensity(light = bpy.data.objects['Point'],
                       domainRandomization = domainRandomization)
```
Used to update the intensity (aka Energy) output of a given light. The ranges of intensity for each light must be specified from the blender UI. Run setupEnvironment.py and you'll see the `Set Intensity Range` button appear in order to set up this setting for each dynamic light.

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `light` | pointer to object | bpy struct | `None` |  |  |
| `domainRandomization` | randomization params | dict |  |  |  |

 -----------
 
## blenderTools.py usage:


```python
convertVertices(scene = bpy.context.scene, 
                cam = bpy.data.objects['Camera'], 
                obj = bpy.data.objects['Cube'], 
                resolutionX = 1920, 
                resolutionY = 1080)
```         
Project an objects 3D world vertecies onto a 2D image plane

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `scene` | pointer to blender scene | bpy struct | `projectedVertices` | [[x, y, depth]] | [[float, float, float]] |
| `cam` | pointer to camera | bpy struct |  |  |  |
| `obj` | pointer to object | bpy struct |  |  |  |
| `resolutionX` | # of pixels | int |  |  |  |
| `resolutionY` | # of pixels | int |  |  |  |

 ----------

```python
updateAbsPosition(obj = bpy.data.objects['Cube'],
                  trajectory = [[0, 0, 0]],
                  timeStep = 0)
```
Update world coordinates of some object of interest, this can be used to itteratively call a given trajectory with desired time steps

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `obj` | pointer to object | bpy struct | `None` |  |  |
| `trajectory` | [[x1, y1, z1]] | [[float, float, float]] |  |  |  |
| `timeStep` | trajectory[idx] | int |  |  |  |

 ----------

```python
rotate(obj = bpy.data.objects['Cube'],
       trajectory = [[0, 0, 0]],
       timeStep = 0)
```
Update euler rotations of some object of interest, this can be used to itteratively call a given trajectory with desired time steps

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `obj` | pointer to object | bpy struct | `None` |  |  |
| `trajectory` | [[theta1, phi1, omega1]] | [float, float, float] |  |  |  |
| `timeStep` | trajectory[idx] | int |  |  |  |

 ----------

```python
cart2Sphere(cart = [0, 0, 0])
```
Convert cartesian coordinates [x, y, z] to spherical coordinates [radius, theta, phi]

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `cart` | [x, y, z] | [float, float, float] | `cart` | [radius, theta, phi] | [float, float, float] |

 ----------

```python
sphere2Cart(cart = [0, 0, 0])
```
Convert spherical coordinates [radius, theta, phi] to cartesian coordinates [x, y, z]
  
| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `cart` | [radius, theta, phi] | [float, float, float] | `cart` | [x, y, z] | [float, float, float] |

 ----------

```python
constraintLimits(obj = bpy.data.objects['NurbsPath'])
```
Extract the maximum coordinates of a 'CURVE', 'PLANE', or 'MESH' blender object

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `obj` | pointer to object | bpy struct | `limits` | [[x, y, z]] | [[float, float, float]] |

 ----------

```python
generatePositions(constraintObj = bpy.data.objects['NurbsPath'], 
                  dynamicObj = bpy.data.objects['Cube'],
                  randomType = 'uniform',
                  count = 100)
```
Generate a random list of 3D world coordinates that obey a desired constraint for translating an object, specify distribution type `'uniform'` or `'normal'`. If `'normal'` specified, the mean location will be the initial position of the object

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `constraintObj` | pointer to object | bpy struct | `positions` | [[x1, y1, z1], [xn, yn, zn]] | [[float, float, float]] |
| `dynamicObj` | pointer to object | bpy struct |  |  |  |
| `randomType` | random distribution type | string |  |  |  |
| `count` | number of positions | int |  |  |  |

 ----------

```python
generateRotations(constraint = [(0.5, -0.2), (0., -1.), (0., 0.)], 
                  dynamicObj = bpy.data.objects['Cube'],
                  randomType = 'uniform',
                  count = 100)
```
Generate a random list of 3D world euler rotations that obey a desired constraint for rotating an object, specify distribution type `'uniform'` or `'normal'`. If `'normal'` specified, the mean location will be the initial orientation of the object

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `constraint` | **in radians** [+/-theta, +/- phi... ] | [(float, float), (float, float), (float, float)] | `rotations` | [[theta1, phi1, omega1], [theta_n, phi_n, omega_n]] | [[float, float, float]] |
| `dynamicObj` | pointer to object | bpy struct |  |  |  |
| `randomType` | random distribution type | string |  |  |  |
| `count` | number of positions | int |  |  |  |

 ----------

```python
visualizeDataStruct(dataObject = bpy.data.objects['Cube'])
```
Create a txt file that displays the structure of a blender data object


## buildDataSet.py usage


# Blender Overview

## bpy usage:

## Conventions

**_starting a new blend file_**:  
Always begin by loading basicEnvironement.blend (see: putLinkToFileHere), this is set up with the proper collection structure for other files that is neccessary to destinguish between static and dynamic parts. 

**_Exporting / importing parts_**:  
  * When exporting cad files from given cad program, ensure you always export as (PUT FILE TYPE HERE). You must convert these files to `.stl` before importing to blender.
  * When Importing parts to blender, always use a consistent scale factor (upper right corner of import pop-up)

**_setting blender origin_**:  
When you begin a new blender file, import the body of the main component first. Then do the following `>selectObject, >right click, >set origin, >origin to center of mass (volume)`. This is imperitive to keep consistent with other datasets. This will be useful for converting coordinates from blender world frame to a robot frame for example.

**_render engine_**:  
Typically choose `'cycles'`


## Jargon:

**_static_**:   
an object, light, or camera that will not move through out entire data generation process

**_dynamic_**:  
an object, light, or camera that will have some type of movement or variation through out data generation

* For parts to move (translate) _**via random generation**_ they must have some kind of constrraint object associated with them. This can be a 
`'CURVE'`, `'PLANE'`, or `'MESH'`. If no constraint is identified, the part will not transalte through out the process. You do NOT need to define a 
constraint in order to move a part manually, this is only required for random position gneration. 

* Dynamic parts also have the ability to transform their features. Objects may be given multiple material slots that can be randomly selected to decrease reliance on color or texture patterns. Lights can be given an intensity range constraint so that they can change how bright the source is on each iteration

**_child_**:    
An object that is dependently paired to another (parent) object. When the child is selected and moved, no changes occur to the parent object or other same level children objects. When the parent object is selected and moved, the child object(s) will also match the parents transformation. to make a desired object or objects children of another part, you must multiselect them all `FIRST`, the multiselect the parent object `LAST`, from the gui: `>right click, >parent, >object`. Multiple levels of child/parent relationships can be formed

**_parent_**:   
An object that is independently paired to another (child) object. When the parent object is selected and moved, all child
objects will match that transformation. To make an object a parent fromm the gui, you must multi select that object `LAST`, `>right click, >parent, >object`

* child/parent example: All wires on an electronic connector are made children of the connector interface object. This way, we can constrain and move just the connector intterface object (the parent), apply trasnformations to just this object, and all children will respond with the same transofrmations. This is handled in blender native c++ behind the scenes and is much more efficient than implementing through python **NOTE: These objects do NOT need to be stored in the same collection. The child parent behavior is always enforced regardless of object storage location**

**_material slot_**:  
A storage location for a new material. material slots are a list that is stroed in the object data struct: bpy.data.objects['Cube'].material_slots[<idx>].material  

**_part dependency_**:  
In an object classification block, you'll find a string entry for `<part dependency>`. This is used when you are classifying an object whos class depends on the location of another object. For example, if you are interested in putting a BBox around the female connector, but the classificvation depends on the location of the male plug, you can enter the ID name of the male plug here to indicate to blender which part defines this class active/inactive.

**_split_**:
A float parameter within the object classification block that allows you to define the percentage of renders that each class should observe. NOTE: The sum of splits across all classes for a single object must equal 1. Example, if an object has one class, the split should be 1.0. If an object has two classes, the splits could be 0.8 and 0.2 etc.

