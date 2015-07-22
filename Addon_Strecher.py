 
def OverloadImageRead(func):
    def wrapper(*args, **kwargs):
        name = args[1]
        image1= func(*args, **kwargs)
        image = np.zeros((image1.shape[0], image1.shape[1], 3))
        if name.find("mask") != -1:
            return image
        #image[:,:,0] = image1
        #image[:,:,1] = image1
        #image[:,:,2] = image1
        print("Overloading",name)
        if name.find("BF") != -1 and name.find("mask") == -1:
            print("Overloaded")
            name2 = name.replace("BF","Fluo1")
            if os.path.exists(name2) and 1:
                #args[1] = name2
                image2 = func(args[0], name2, **kwargs)
                print np.amax(image2)
                image2 = image2/np.amax(image2)
                #image2 = image2**2
                image2 = image2*256
                alhpa = image2/256.
                print np.amax(image2)
                #image[:,:,2] = (image[:,:,2]*(1-alhpa))+(image2*alhpa)
                image[:,:,1] = image2
            name2 = name.replace("BF","Fluo1")
            name2 = os.path.join(srcpath2, os.path.split(name2)[1])
            print("----",name2)
            if os.path.exists(name2) and 1:
                #args[1] = name2
                image2 = func(args[0], name2, **kwargs)
                image2 = image2/np.amax(image2)
                #image2 = image2**2
                image2 = image2*256
                alhpa = image2/256.
                print(np.amax(image2))
                #image[:,:,0] = (image[:,:,0]*(1-alhpa))+(image2*alhpa)
                image[:,:,2] = image2
            name2 = name.replace("BF","Fluo2")
            name2 = os.path.join(srcpath2, os.path.split(name2)[1])
            print("----",name2)
            if os.path.exists(name2) and 1:
                #args[1] = name2
                image2 = func(args[0], name2, **kwargs)
                image2 = image2/np.amax(image2)
                #image2 = image2**2
                image2 = image2*256
                alhpa = image2/256.
                print np.amax(image2)
                #image[:,:,0] = (image[:,:,0]*(1-alhpa))+(image2*alhpa)
                image[:,:,0] = image2
#            image[:,:,2] = 0
        return image
    return wrapper

def OverloadKeyPressEvent(func):
    def wrapper(*args, **kwargs):
        event = args[1]
        self_class = args[0]
        if event.key() == QtCore.Qt.Key_E:
            print("E")
            fp = open( os.path.join(srcpath, "results.csv"),'w')
            filenames = glob.glob(os.path.join(srcpath,"*_pos.txt"))
            for filename in filenames:
                data = np.loadtxt(filename)
                if len(data.shape) == 1:
                    data = np.array( [data])
                print data.shape, len(data.shape)
                fp.write(os.path.split(filename)[1][:-8]+";")
                fp.write(str(sum(data[:,2]==0))+";")
                fp.write(str(sum(data[:,2]==1))+";")
                fp.write(str(sum(data[:,2]==2))+";\n")    
            fp.close()
                
                
            return
        if event.key() == QtCore.Qt.Key_Left:
            self_class.SaveMaskAndPoints()
            self_class.drawPath = QPainterPath()
            self_class.drawPathItem.setPath(self_class.drawPath)

            old_pos = self_class.MediaHandler.getCurrentPos()
            found = 0
            while self_class.MediaHandler.setCurrentPos(self_class.MediaHandler.getCurrentPos() - 1):
                if self_class.MediaHandler.getCurrentFilename()[1].find("BF") != -1:
                    self_class.UpdateImage()
                    found = 1
                    break
            if not found:
                self_class.MediaHandler.setCurrentPos(old_pos)
            return
        if event.key() == QtCore.Qt.Key_Right:
            self_class.SaveMaskAndPoints()
            self_class.drawPath = QPainterPath()
            self_class.drawPathItem.setPath(self_class.drawPath)

            old_pos = self_class.MediaHandler.getCurrentPos()
            found = 0
            while self_class.MediaHandler.setCurrentPos(self_class.MediaHandler.getCurrentPos() + 1):
                if self_class.MediaHandler.getCurrentFilename()[1].find("BF") != -1:
                    self_class.UpdateImage()
                    found = 1
                    break
            if not found:
                self_class.MediaHandler.setCurrentPos(old_pos)
            return
        return func(*args, **kwargs)
    return wrapper


MediaHandler.ReadImage = OverloadImageRead(MediaHandler.ReadImage)
DrawImage.keyPressEvent = OverloadKeyPressEvent(DrawImage.keyPressEvent)