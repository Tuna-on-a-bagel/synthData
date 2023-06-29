SynthGen1 Usage:

    The main goal of this tool is to provide a structure of handling objects within a scene that is ideal for data generation with desirable traits

    NOTE: Before you run this file, you must run spawnDirs.py to create the directory structure neccessary for saving file types

--------------------------------------------------------------------------------------------------------------------------------------------------  
    Main file Parameters: 
                                                # Parameter Options             Discription
                                                ##########################      #############################################################
        renders
            
            'count':            <int>                                           This should be the desired number of renders you wish to create
        
        paths:                                                                  ** see spawnDirs.py README.txt for more information on directory structure **
            
            'fileName':         <string>                                        This is the name that will be associate with each render. Do not include the file type, this will be 
                                                                                added automatically. Each image will be enumerated as well
            
            'root':             <string>                                        This should be the path to the main forlder that contains your data set. NOTE: you must run spawnDirs.py
                                                                                before hand.
            
            'renders':          <string>                                        DO NOT CHANGE - path to render folder
            
            'csv':              <string>                                        DO NOT CHANGE - path to csv folder
            
            'jsonFile':         <string>                                        DO NOT CHANGE - path to jsonFile (for gcp usage)
            
            'projectionMat':    <string>                                        DO NOT CHANGE - path to <fileName>.npy array that stores coordinates of all vertecies of class objects
            
            'descriptionJson':  <string>                                        **NOT IMPLEMENTED** DO NOT CHANGE - path to json file that will be used to build super/sub sets, not finished implementing


        cameraParams:
            
            'properties':

                'monocular/stereo': <string>     [<'monocular'>, <'stereo'>]    Identifying paramter for blender to detect if you want to take stereo images or monoculare images                     
                
                'baselineDist':     <float>                                     [mm] distance between to two optical centers of each camera                    
                
                'focalLength_mm':   <float>                                     [mm] focal length of the camera, it is imperitive this matches the actual camera specs of your hardware                      
                
                'sensorWidth_mm':   <float>                                     [mm] width of your hardware sensor, check manufacturer datasheet                      
                
                'sensorHeight_mm':  <float>                                     [mm] height of your hardware sensor, check manufacturer datasheet

            'tracking':                 
                
                'active':           <Bool>                                      If set to True, camera will track bpy.data.objects['cameratrackingPoint']. This object can be changed but 
                                                                                this change must be reflected in the .blend file, either from the blender UI or from bpy. I **believe** that
                                                                                the camera tracking constraint must be some type of empty such as axis or something, but this may not be true
                
                'positions':        <list()>                                    **NOT IMPLEMENTED** You can store a list fo 3D coordinates for the tracking object to follow, this should be 
                                                                                done through scripting

            'translation': 
                                
                'active':           <Bool>                                      if set to True, camera translate within constraint object **must have a constraint**
                
                'random':          
                    
                    'method':       <string>       [<'uniform'>, <'normal'>]    Uniform/Normal random distributions
                    
                    'mean':         <string>       [<'intiLoc'>]                centered at intial location **only used for noraml distribution**
                    
                    'sigma':        <float>                                     variance for normal distribution sampling **only used for noraml distribution**
                                   
                              
        domainRandomization:
                                
            'lighting':                                          
                                        
                'active':           <Bool>                                      If true, dynamic lights will be altered
                
                'translation':
                                                
                    'random':    
                                                    
                        'method':   <string>       [<'uniform'>, <'normal'>]    Uniform/Normal random distributions
                        
                        'mean':     <stirng>       [<'intiLoc'>]                centered at intial location **only used for noraml distribution**
                        
                        'sigma':    <float>        [<Float>]                    variance for normal distribution sampling **only used for noraml distribution**
                                                    
                'intensity':
                                                
                    'random':    
                                                    
                        'method':   <string>        [<'uniform'>, <'normal'>]   Uniform/Normal random distributions
                        
                        'mean':     <string>        [<'intiLoc'>]               centered at intial location **only used for noraml distribution**
                        
                        'sigma':    <float>         [<Float>]                   variance for normal distribution sampling **only used for noraml distribution**

                'material':                                                      # '''NOT IMPLEMENTED'''       Control material randomization of objects
                                        
                    'active':        <Bool>         [<True>, <False>]  
                    
                    'assetRootDir':  <string>       [<None>, <Path_to_assets>]  None: pulls from default environment assets, or supply path to custom asset folder  
                                                               

                'environment':                                          # '''NOT IMPLEMENTED'''
                                    
                    'dust':          <Bool>
                    
                    'abrasion':      <Bool>
                                                     
                            

        generalinfo:
                            
            'source':               "synthetic-gen",
            
            'part':                 "ADAS-ECU",

            'path_to_blendFile':    None,

            'renderMethod':         'cycles',
            
            'resolution_px':        760,
            
            'resolution_py':        556,

            'imageIDs':             []                                               list of image names
                            
--------------------------------------------------------------------------------------------------------------------------------------------------  
Blend file structure:

    Collections:                    collections are a blender data structure that are used to store groups of objects. these are called
                                    with bpy.data.collections['<NameOfCollection>']. The objects within this collection can be returned
                                    by calling bpy.data.collections['<NameOfCollection>'].objects

        Camera:                     Store all camera objects in this collection including camera constraints and tracking objects. Call this
                                    collection with bpy.data.collections['Camera'].objects

        Lighting:

            staticLights:           Store all static light objects in this collection. Call this with bpy.data.collections['staticLights'].objects

            dynamicLights:          Store all dynamic light objects and their constraints in this collection. Call this with bpy.data.collections['dynamicLights'].objects               

        Parts:

            wires:                  This collection is only for organization, each bezier curve to make a wire must be its own uniqure object, so scenes
                                    can end up with hundreds of these and navigating the gui file list can become cumberson. 


--------------------------------------------------------------------------------------------------------------------------------------------------  
naming conventions:

    Jargon:

        static:         an object, light, or camera that will not move through out entire data generation process

        dynamic:        an object, light, or camera that will have some type of movement or variation through out data generation

                            - For parts to move (translate) **via random generation** they must have some kind of constrraint object associated with them. This can be a 
                            'CURVE', 'PLANE', or 'MESH'. If no constraint is identified, the part will not transalte through out the process. You do NOT need to define a 
                            constraint in order to move a part manually, this is only required for random position gneration. 

                            - Dynamic parts also have the ability to transform their features. Objects may be given multiple material slots that can be randomly selected
                              to decrease reliance on color or texture patterns. Lights can be given an intensity range constraint so that they can change how bright 
                              the source is on each iteration

        child:          An object that is dependently paired to another (parent) object. When the child is selected and moved, no changes occur to the parent object. When
                        the parent object is selected and moved, the child object will also match the parents transformation. to make a desired object or objects children
                        of another part, you must multiselect them all FIRST, the multiselect the parent object LAST, from the gui: <>right click, >parent, >object


        parent:         An object that is independently paired to another (child) object. When the parent object is selected and moved, all child objects will match 
                        that transformation. To make an object a parent fromm the gui, you must multi select that object LAST, <>right click, >parent, >object

            child/parent example:

                        All wires on an electronic connector are made children of the connector interface object. This way, we can constrain and move just the connector intterface
                        object (the parent), apply trasnformations to just this object, and all children will respond with the same transofrmations. This is handled in blender native
                        c++ behind the scenes and is much more efficient than implementing through python

                        NOTE: These objects do NOT need to be stored in the same collection. The child parent behavior is always enforced regardless of object storage location



    
