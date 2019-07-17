from __future__ import division, print_function
from PIL import Image
from osgeo import gdal
from subprocess import call
from multiprocessing import Process, Pool, freeze_support
from itertools import product
import io, os, sys, numpy as np, time, math, traceback
'''
Each image will be divided in threadedCols*threadedRows subimages and each
thread will work with one of them
'''
threadedCols = 2
threadedRows = 2
#Thread-safe printing
print = lambda x: sys.stdout.write("%s\n" % x)

def computeMapboxHeight(height):
    
    value = int((height + 10000)*10)
    
    r = value>>16
    g = (value>>8 & 0x0000FF)
    b = value & 0x0000FF

    return (r, g, b)

def MapboxHeight2Height(color):
    return -10000 + ((color[0] * 256 * 256 + color[1] * 256 + color[2]) * 0.1)

def timeString(floatSeconds):
    timeStr = ""
    seconds = int(floatSeconds)

    if(seconds < 60):
        timeStr = "{} seconds".format(seconds)
    else:
        minutes = seconds / 60
        remainingSeconds = seconds % 60
        
        if(minutes<60):
            timeStr = "{} minutes, {} seconds".format(int(minutes), remainingSeconds)
        else:
            hours = minutes / 60
            remainingMinutes = minutes % 60
            timeStr = "{} hours, {} minutes, {} seconds".format(int(hours), remainingMinutes, remainingSeconds)

    return timeStr

def initializer(imageWidth, imageHeight, outputPath, 
    pixelWidthBase, pixelHeightBase, leftPixelCenterBase, 
    topPixelCenterBase, subImageWidth, subImageHeight):
    global numPixels, numPixelsPC, numPixelsDone
    global totalPixelsDone, startTime, threadedRows
    global threadedCols, pixelWidth, pixelHeight
    global leftPixelCenter, topPixelCenter
    global outputFilePath
    global columnWidth, rowHeight

    numPixels = imageWidth*imageHeight
    numPixelsPC = int(numPixels/100)
    numPixelsDone = 0
    totalPixelsDone = 0
    startTime = time.time()
    outputFilePath = outputPath
    pixelWidth = pixelWidthBase
    pixelHeight = pixelHeightBase
    leftPixelCenter = leftPixelCenterBase
    topPixelCenter = topPixelCenterBase
    columnWidth = subImageWidth
    rowHeight = subImageHeight

    print(str(numPixels) + " pixels to go")

def generateImage(demFile, outputFile):
    global threadedRows, threadedCols, pixelWidth, pixelHeight
    global leftPixelCenter, topPixelCenter, outputFilePath

    demImage = gdal.Open(demFile, gdal.GA_ReadOnly)
    outputFilePath = outputFile
    imageWidth = demImage.RasterXSize
    imageHeight = demImage.RasterYSize
    demBand = demImage.GetRasterBand(1)
    transform = demImage.GetGeoTransform()
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    leftPixelCenter = transform[0] + pixelWidth/2
    topPixelCenter = transform[3] + pixelHeight/2

    imageChunks = []

    print("###########" + demFile + "###########")
    print("Image size: " + str(imageWidth) + ", " + str(imageHeight))
    print("Pixel size: " + str(pixelHeight) + ", " + str(pixelHeight))
    print("Top-left pixel center: " + str(leftPixelCenter) + ", " + str(topPixelCenter))

    width = int(math.ceil(imageWidth / threadedCols))
    height = int(math.ceil(imageHeight / threadedRows))
    for i in range(threadedRows):
        imageChunks.append([])
        for j in range(threadedCols):
            startWidth = j * width
            startHeight = i * height
            realWidth = width if startWidth+width < imageWidth else imageWidth - startWidth
            realHeight = height if startHeight+height < imageHeight else imageHeight - startHeight
            demData = demBand.ReadAsArray(startWidth, startHeight, realWidth, realHeight)

            imageChunks[i].append(demData.transpose())
            print("Chunk " + str(i) + "-" + str(j) + ": " + str(startWidth) + "x" + str(startHeight) + " to " + str(startWidth+realWidth) + "x" + str(startHeight+realHeight))

    print("#########################################################")

    dispatcher(imageChunks, imageWidth, imageHeight, pixelWidth, pixelHeight,
        leftPixelCenter, topPixelCenter, width, height)

    demImage = None

def dispatcher(demData, imageWidth, imageHeight, pixelWidth, pixelHeight,
    leftPixelCenter, topPixelCenter, subImageWidth, subImageHeight):
    global threadedRows, threadedCols, outputFilePath

    threads = []
    numThreads = threadedCols*threadedRows
    threadParameters = (imageWidth, imageHeight, outputFilePath,
            pixelWidth, pixelHeight, leftPixelCenter, topPixelCenter,
            subImageWidth, subImageHeight)
    if(numThreads > 1):
        print("Multithreaded")
        args = []
        for threadRowIndex in range(threadedRows):
            for threadColIndex in range(threadedCols):
                args.append((threadRowIndex, threadColIndex, 
                    demData[threadRowIndex][threadColIndex]))

        p = Pool(numThreads, initializer, threadParameters)
        p.map(work_unpack, args)
        p.close()
        p.join()

    else:
        print("Singlethreaded")
        initializer(*threadParameters)
        work(0, 0, demData[0][0])

def work(subImageRow, subImageCol, demData):
    global numPixels, numPixelsPC, numPixelsDone
    global totalPixelsDone, startTime, threadedRows
    global threadedCols

    (width, height) = demData.shape
    print("Working on " + str(width) + " " + str(height))
    outData = np.zeros((width, height, 3), dtype=np.uint8)

    for i in range(width):
        for j in range(height):
            demHeight = demData[i][j]
            color = computeMapboxHeight(demHeight)
            outData[i][j][0] = color[0]
            outData[i][j][1] = color[1]
            outData[i][j][2] = color[2]
            numPixelsDone += threadedCols*threadedRows
            totalPixelsDone += threadedCols*threadedRows

        if(subImageRow == 0 and subImageCol == 0 and numPixelsDone > numPixelsPC):
            timeDiff = time.time() - startTime
            pixelsDonePC = (totalPixelsDone/numPixels)*100
            remainingPC = 100 - pixelsDonePC
            remainingTime = (remainingPC * timeDiff) /pixelsDonePC
            print(str(pixelsDonePC) + "% pixels done " + timeString(timeDiff) + ". " + timeString(remainingTime) + " remaining.")
            numPixelsDone = 0

    saveFile(subImageRow, subImageCol, outData)

def work_unpack(args):
    return work(*args)

def saveFile(subImageRow, subImageCol, outputData):

    global pixelWidth, pixelHeight
    global leftPixelCenter, topPixelCenter
    global outputFilePath
    global columnWidth, rowHeight

    subImageLeft = leftPixelCenter + subImageCol*columnWidth*pixelWidth
    subImageTop = topPixelCenter + subImageRow*rowHeight*pixelHeight
    newName = outputFilePath[:-4] + "_" + str(subImageRow) + "_" + str(subImageCol)

    print("Saving " + str(subImageRow) + " " + str(subImageCol) + " data:")
    print("Saving PNG file")
    output = Image.fromarray(outputData.swapaxes(0,1), 'RGB')
    output.save('./{}.png'.format(newName))

    print("Generating PGW file")
    output = "{}.pgw".format(newName)
    with open(output, "w") as pgwFile:
        pgwFile.write("{0:.50f}\n".format(pixelWidth))
        pgwFile.write("{0:.50f}\n".format(0.0))	#TODO: Compute skew parameters
        pgwFile.write("{0:.50f}\n".format(0.0))	#TODO: Compute skew parameters
        pgwFile.write("{0:.50f}\n".format(pixelHeight))
        pgwFile.write("{0:.50f}\n".format(subImageLeft))
        pgwFile.write("{0:.50f}".format(subImageTop))

if __name__ == "__main__":
    freeze_support()
    try: 
        if (1 != len(sys.argv)):
            demFile = sys.argv[1]
            outFile = sys.argv[2]

            generateImage(demFile, outFile)
        else:
            print("Not enough parameters (demFile.tif outputFile.png)")

    except:
        traceback.print_exc()