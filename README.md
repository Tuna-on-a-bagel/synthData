# Synthetic Data generation overview

Blender version:    3.6.0

Python Version:     3.9.13

This package is designed to collaborate with blender files in order to generate synthetic images for training AI vision models. The current implementation is able to provide ground truth or custom bounding boxes for object detection. There are several utility files associated with this package:
  * spawDirs.py:          Used to create consistent directory structures across all datasets
  * setupEnvironment.py   Used to register custom classes to aid in synthetic data generation from blender UI
  * synthGen.py:          Handles .blend file and generation parameters, renders and stores images, initial csv, and vertex projectoin array
  * blenderTools.py:      Stores functions called from synthGen.py
  * buildDataSet.py:      Used to handle unique variations of csvv/jsonl file creation, also handles identifying image coordinates for bounding boxes

The majority of the work that will be done is through the blender UI. A tutorial video for working with this specific package can be found
at: _LinkToVideo_

All of these modules utilize the blender python api bpy. Documentation for bpy can be found here: https://docs.blender.org/api/current/index.html
NOTE: this documentation is fairly weak, you may encounter many problems when calling certain functions. There have been many changes made between bpy 2.8 and 3.5, but the 3.5 documentation is lagging behind.

## spawnDirs.py:

This file must be run prior to any other process. This will generate a consistent directory structure between all data sets that might prevent issues later on when locating files. The general structure for each datset will look like:

    root directory:
    |-- <fileName>
        |--  csvfile:
        |    |--   <fileName>.csv                   csv file storing excess information including both BBox coordinates and camera locations etc
        |    |--   <fileName>_gcp.csv               csv file that removes excess information, structured for gcp usage
        |   
        |--  descriptionJson:
        |    |--   <fileName>_description.json      json used to store excess scene information for building/extracting super/sub sets 
        |
        |--  jsonFile:
        |    |--   <fileName>.jsonl                 jsonl for gcp usage
        |
        |--  projectionMat:
        |    |--   <fileName>.npy                   numpy array storing all vertext projections to image plane of objects with classification
        |                                           association in blender file
        |--  renders:
        |    |--   0<fileName>.png
        |    |--   1<fileName>.png
        |    |--   ...
        |    |--   n<fileName>.png

## syntheGen1.py:
        
This file handles the majority of the generation procedures


## blenderTools.py:

**convertVertices():** Project some set of world 3D coordinates onto a 2D plane, used to project list of bpy object vertices onto the camera image plane

| something                                                      |
| -------------------------------------------------------------- |                   
| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `scene` | bpy.context.scene | bpy struct | `projectedVertices` | [[x, y, depth]] | nested lists |
| `cam` | camera object | bpy struct |  |  |  |
| `obj` | object of interest | bpy struct |  |  |  |
| `resolutionX` | # of pixels | int() |  |  |  |
| `resolutionY` | # of pixels | int() |  |  |  |


**updateAbsPosition():** Update world coordinates of some object of interest, this can be used to itteratively call a given trajectory with desired time steps

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `obj` | object of interest | bpy struct | `None` |  |  |
| `trajectory` | 3D coordinates | [[x1, y1, z1], [x2, y2, z2]] |  |  |  |
| `timeStep` | trajectory[idx] | int |  |  |  |


**rotate():** Update euler rotations of some object of interest, this can be used to itteratively call a given trajectory with desired time steps

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `obj` | object of interest | bpy struct | `None` |  |  |
| `trajectory` | 3D rotations | [[x1, y1, z1], [x2, y2, z2]] |  |  |  |
| `timeStep` | trajectory[idx] | int |  |  |  |


**cart2Sphere():** Convert cartesian coordinates [x, y, z] to spherical coordinates [radius, theta, phi]

| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `cart` | [x, y, z] | [float, float, float] | `cart` | [radius, theta, phi] | [float, float, float] |

**sphere2Cart():** Convert spherical coordinates [radius, theta, phi] to cartesian coordinates [x, y, z]
  
| Parameters | Description | type | Returns | Description | type |
| ---------- | ----------- | ---- | ------- | ----------- | ---- |
| `cart` | [radius, theta, phi] | [float, float, float] | `cart` | [x, y, z] | [float, float, float] |


## Blender / bpy usage:

## Conventions / Jargon:



**_static_**:   an object, light, or camera that will not move through out entire data generation process

**_dynamic_**:  an object, light, or camera that will have some type of movement or variation through out data generation

* For parts to move (translate) _**via random generation**_ they must have some kind of constrraint object associated with them. This can be a 
'CURVE', 'PLANE', or 'MESH'. If no constraint is identified, the part will not transalte through out the process. You do NOT need to define a 
constraint in order to move a part manually, this is only required for random position gneration. 

* Dynamic parts also have the ability to transform their features. Objects may be given multiple material slots that can be randomly selected
    to decrease reliance on color or texture patterns. Lights can be given an intensity range constraint so that they can change how bright 
    the source is on each iteration

**_child_**:    An object that is dependently paired to another (parent) object. When the child is selected and moved, no changes occur to the
            parent object. When the parent object is selected and moved, the child object will also match the parents transformation. to make a desired object or objects children of another part, you must multiselect them all FIRST, the multiselect the parent object LAST, from the gui: >right click, >parent, >object


**_parent_**:   An object that is independently paired to another (child) object. When the parent object is selected and moved, all child
            objects will match that transformation. To make an object a parent fromm the gui, you must multi select that object LAST, >right click, >parent, >object

* child/parent example: All wires on an electronic connector are made children of the connector interface object. This way, we can constrain and
                        move just the connector intterface object (the parent), apply trasnformations to just this object, and all children will respond with the same transofrmations. This is handled in blender native c++ behind the scenes and is much more efficient than implementing through python **NOTE: These objects do NOT need to be stored in the same collection. The child parent behavior is always enforced regardless of object storage location**


