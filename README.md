# Synthetic Data generation

This package is designed to collaborate with blender files in order to generate synthetic images for training AI vision models. The current implementation
is able to provide ground truth or custom bounding boxes for object detection. There are several utility files associated with this package:
  * spawDirs.py:          Used to create consistent directory structures across all datasets
  * synthGen<x>.py:       Handles .blend file and generation parameters, renders and stores images, initial csv, and vertex projectoin array
  * blenderTools<x>.py:   Stores functions called from synthGen<x>.py
  * buildDataSet<x>.py:   Used to handle unique variations of csvv/jsonl file creation, also handles identifying image coordinates for bounding boxes

The majority of the work that will be done is through the blender UI. A tutorial video for working with this specific package can be found
at: <put link to video here>

all of these modules utilize the blender python api bpy. Documentation for bpy can be found here: https://docs.blender.org/api/current/index.html
NOTE: this documentation is fairly weak, you may encounter many problems when calling certain functionns. There have been many changes made between bpy 2.8 and 3.5,

