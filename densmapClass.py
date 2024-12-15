from geopy.distance import geodesic
import numpy as np

def latlng2meter(locO, locA):
    Olat, Olng = locO
    Alat, Alng = locA
    #lat diff                                                  
    x = geodesic((Olat,Olng),(Alat,Olng)).m
    #lng diff
    y = geodesic((Olat,Olng),(Olat,Alng)).m
    return x,y

def loc2Index(locO,pois,partitionSize):
    poiset = np.apply_along_axis(lambda x: latlng2meter(locO, x), axis=1, arr=pois)
    poiIndex = poiset
    poiIndex = (poiIndex//partitionSize).astype(int)
    return poiIndex


class densMap():
    def __init__(self, partitionSize, r,poiset,locO):
        self.partitionSize = partitionSize
        self.locO=locO
        self.r = r
        self.densmap = self.getmap(poiset)
        
        
    def getmap(self,poiIndex):
        partitionSize = self.partitionSize
        r = self.r
        locO =self.locO
        
        # xMax, yMax = np.max(poiset, axis=0)
        # xSize = -((-xMax)//partitionSize)
        # ySize = -((-yMax)//partitionSize)
        # if xSize < 1: xSize +=1
        # if ySize < 1: ySize +=1
        xSize, ySize = np.max(poiIndex, axis=0)
        xSize +=1
        ySize +=1
        # poiIndex = poiset
        # poiIndex = (poiIndex//partitionSize).astype(int)
        R = int(-((-r)//partitionSize))
        center = R//2
        R = center*2 +1
        potential = np.zeros((R,R))
        for i in range(R):
            for j in range(R):
                if i == center and j== center:
                    potential[i,j] = 1
                else:
                    potential[i,j] = 1/(abs(i-center)**2+abs(j-center)**2)
        field = np.zeros((int(xSize+2*center),int(ySize+2*center)))
        # print(field.shape)
        for k in range(len(poiIndex[:,0])):
            x,y = poiIndex[k,:]
            x +=center
            y +=center
            # print(x,y)
            # print( field[x-center:x+center+1, y-center:y+center+1].shape)
            # print((potential/partitionSize).shape)
            field[x-center:x+center+1, y-center:y+center+1]+=potential 
        return field[center:-center,center:-center]

