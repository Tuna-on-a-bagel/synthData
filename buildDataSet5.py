import cv2 as cv
import numpy as np
import pandas as pd
import json
import random
import copy
import dataTools #this is a personal module


'''Version 3: built for the following data set struct:
                
                root/dataSets/
                        |   subjectDir/
                                |   dataSetName/
                                        |   csvFile/
                                        |   jsonFile/
                                        |   projectionMat/
                                        |   renders/
                                        
        This version will create an instance for each selected object - useful for adas'''



def main(fileName, renderCount, rootDir, renderPath, vertexPath, csvPath, jsonPath, gcpPath, split):
    
    
    #dataTools.rotateImageDirectory(renderPath=renderPath)
    
    #.npy file that stores all projection matricies (output from blender)
    vertMat = np.load(vertexPath, allow_pickle=True)

    #csv object
    data_csv = pd.read_csv(csvPath)
    classification = data_csv.loc[0, "classification"]


    #list for storing json objects, will be converted to .jsonl
    data_json_list = []

    tempfileName = data_csv.loc[0, 'fileName']
    print(tempfileName)

    #get image resolutions
    imgPath = renderPath + tempfileName
    img = cv.imread(imgPath, 1)

    resolutionY, resolutionX = np.shape(img)[0], np.shape(img)[1]

    print(f'xRes: { resolutionX}, yRes: {resolutionY}')

    #random index splits based on split requirements
    train_index, test_index, validation_index = dataTools.splitData(renderCount, split)
    print(f"train_index: {train_index}, test_index:{test_index}, validation_index:{validation_index}")

    numberOfImages = np.shape(vertMat)[0]
    print(numberOfImages)
    

    for i in range(numberOfImages): #this should be the number of images
    
        #data_csv.loc[i, 'fileName'] = gcpPath + fileName
        numberOfObjects = np.shape(vertMat)[1]
       
        for j in range(numberOfObjects): #this should be the number of selected parts in each image
            
            #tempfileName = data_csv.loc[i*numberOfObjects + j, 'fileName']

            #data_csv.loc[i*numberOfObjects + j, 'fileName'] = tempfileName
            #sets for identifying max values
            allX = set()
            allY = set()

            #extract image specific vertecies 
            vertices = vertMat[i][j]

            #build set for each dim
            for k in range(len(vertices)):
                x, y, _ = vertices[k]
                allX.add(int(x))
                allY.add(int(y))

            #gather BBox coordinates
            xMin = int(min(allX))
            xMax = int(max(allX))
            yMin = int(min(allY))
            yMax = int(max(allY))
            #print(f'i:{i}, j:{j},   xm: {xMin}, ym: {yMin}, xM:{xMax}, yM:{yMax}')

            #Normalize them
            xMin, xMax, yMin, yMax = dataTools.normalizeCoordinates(xMin, xMax, yMin, yMax, resolutionX, resolutionY)

            #rotate by 180 (Specific for RCM):
            xMaxHolder = copy.copy(xMax)
            xMinHolder = copy.copy(xMin)
            yMaxHolder = copy.copy(yMax)
            yMinHolder = copy.copy(yMin)
            #xMax = 1 - xMinHolder
            #xMin = 1 - xMaxHolder
            #yMax = 1 - yMinHolder
            #yMin = 1 - yMaxHolder

            #update csv
            data_csv.loc[i*numberOfObjects + j, 'xMin'] = xMin
            data_csv.loc[i*numberOfObjects + j, 'xMax'] = xMax
            data_csv.loc[i*numberOfObjects + j, 'yMin'] = yMin
            data_csv.loc[i*numberOfObjects + j, 'yMax'] = yMax

            
            

            #dataTools.renameImage(renderPath + str(i) + fileName + '.png', renderPath + str(i) + fileName + data_csv.loc[i, 'classification'] + '.png')
            

            
            #vertex AI GCP stuff:
            displayName = data_csv.loc[i*numberOfObjects + j, "classification"]
            print(f'i*numObjects + j: {i*numberOfObjects + j}')
            
            '''
            Format from GCP intro page:

                j = {"imageGcsUri":"gs://bucket/filename.ext",
                    "classificationAnnotation": {"displayName": "LABEL",
                                                "annotationResourceLabels": {"aiplatform.googleapis.com/annotation_set_name": "displayName",
                                                                            "env": "prod"
                                                                            }
                                                },
                    "dataItemResourceLabels": {"aiplatform.googleapis.com/ml_use": "training/test/validation"}
                    }'''
            
            annotationResourceLabels = dict({"airplatform.googleapis.com/annotation_set_name":"7787165759397953536"})
            if i in train_index: TTV ="train"
            elif i in test_index: TTV ="test"
            elif i in validation_index: TTV ="validation"

            dataItemResourceLabels = dict({"airplatform.googleapis.com/ml_use":TTV})
            boundingBoxAnnotations = [dict({"displayName":displayName,
                                            "xMin":xMin,
                                            "xMax":xMax,
                                            "yMin":yMin,
                                            "yMax":yMax,
                                            "annotationResourceLabels":annotationResourceLabels})]
            
            js = {"imageGcsUri":gcpPath+fileName+".png",
                "boundingBoxAnnotations":boundingBoxAnnotations,
                "dataItemResourceLabels":dataItemResourceLabels}
            
            data_json_list.append(js)


            data_csv.loc[i*numberOfObjects + j, 'use'] = TTV

            tempFileName = str(data_csv.loc[i*numberOfObjects + j, 'fileName'])

            data_csv.loc[i*numberOfObjects + j, 'fileName'] = gcpPath + tempFileName

            data_csv.to_csv(csvPath, index=False)
    
    dataTools.Json2Jsonl(data_json_list, fileName,outPath=jsonPath)
    
    
    
    return


if __name__ == "__main__":

    fileName = "synthGenT3"

    rootDir = "/home/tuna/Documents/driving/Vision/syntheticData/dataSets/ADAS/"
    renderPath = rootDir + fileName + "/renders/"
    csvPath = rootDir + fileName + "/csvFile/" + fileName + ".csv"
    jsonPath = rootDir + fileName + "/jsonFile/"
    vertexPath = rootDir + fileName + "/projectionMat/" + fileName + ".npy"
    gcpPath = "gs://metapix-advmfg-bucket-d/mtdc_fvis_synthetic/training_datasets/ADAS/trial1/"

    #data splits
    split = [0.80, 0.0, 0.2] #[Train, test, validation] ***sum(split) = 1***

    renderCount = 20

    main(fileName =         fileName,
         renderCount=       renderCount, 
         rootDir=           rootDir, 
         renderPath=        renderPath, 
         vertexPath=        vertexPath,
         csvPath=           csvPath, 
         jsonPath=          jsonPath, 
         gcpPath=           gcpPath, 
         split =            split)
    