import os

def spawnDirStruct(root, subjectDir, fileName):
    ''' Params:
            root:           parent folder, in most cases should be "/home/tuna/Documents/driving/Vision/syntheticData/dataSets/"
            subjectDir:     folder that will contain subsets
            fileName:       will be used as data set folder name

        Structure:
            root/subjectDir/
                        |   fileName/
                            |   csvFiles/           #stores gcp csv
                            |   descriptionJson/    #stored json that describes entire dataset
                            |   jsonFiles/          #stores gcp json
                            |   projectionMat/      #stores vertex projection matrix
                            |   renders/            #stores all images
        '''
    
    try:
        os.mkdir(root + subjectDir) #checks if subject already exists already exists
    except FileExistsError:
        pass

    try:
        os.mkdir(root + subjectDir + fileName + "/")
    except:
        print("Caution: this folder already exists")
        return
    
    os.mkdir(root + subjectDir + fileName + "/renders/")
    os.mkdir(root + subjectDir + fileName + "/csvFile/")
    os.mkdir(root + subjectDir + fileName + "/jsonFile/")
    os.mkdir(root + subjectDir + fileName + "/projectionMat/")
    os.mkdir(root + subjectDir + fileName + "/descriptionJson/")       

"/home/tuna/Documents/driving/Vision/syntheticData/dataSets/"
if __name__ == "__main__":

    root = "/media/tuna/Pauls_USBA/"
    subjectDir = 'adas/trial5/'

    fileName = "synthGenT5"

    spawnDirStruct(root=root, subjectDir=subjectDir, fileName=fileName)


