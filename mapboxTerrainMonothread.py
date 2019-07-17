from __future__ import division
from PIL import Image
from osgeo import gdal
from subprocess import call
import io, os, sys, numpy as np, time

def computeMapboxHeight(height):
	
	value = int((height + 10000)*10)
	
	r = value>>16
	g = (value>>8 & 0x0000FF)
	b = value & 0x0000FF

	return (r, g, b)

def MapboxHeight2Height(color):
	return -10000 + ((color[0] * 256 * 256 + color[1] * 256 + color[2]) * 0.1)

def saveFile(outputData, path):
	output = Image.fromarray(outputData, 'RGB')
	output.save('./{}'.format(path))

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

def generateImage(demFile, outputFile):
	demImage = gdal.Open(demFile, gdal.GA_ReadOnly)
	demBand = demImage.GetRasterBand(1)
	demData = demBand.ReadAsArray()
	[width, height] = demData.shape

	topLeft = demData[0, 0]
	topRight = demData[0, height-1]
	bottomLeft = demData[width-1, 0]
	bottomRight = demData[width-1, height-1]
	center = demData[(int(width/2)), (int(height/2))]

	outData = np.zeros((width, height, 3), dtype=np.uint8)
	numPixels = width*height
	numPixelsPC = int(numPixels/100)
	numPixelsDone = 0
	totalPixelsDone = 0
	startTime = time.time()

	for i in range(0, width):
		for j in range(0, height):
			demHeight = demData[i][j]
			color = computeMapboxHeight(demHeight)
			outData[i][j][0] = color[0]
			outData[i][j][1] = color[1]
			outData[i][j][2] = color[2]
			numPixelsDone += 1
			totalPixelsDone += 1
		if(numPixelsDone > numPixelsPC):
			timeDiff = time.time() - startTime
			pixelsDonePC = (totalPixelsDone/numPixels)*100
			remainingPC = 100 - pixelsDonePC
			remainingTime = (remainingPC * timeDiff) /pixelsDonePC
			print pixelsDonePC, "% pixels done in", timeString(timeDiff), ".", timeString(remainingTime), "remaining."
			numPixelsDone = 0

	print "Original top left data: ", topLeft
	print "Encoded top left data: ", MapboxHeight2Height(outData[0, 0])
	print "Original top right data: ", topRight
	print "Encoded top right data: ",  MapboxHeight2Height(outData[0, height-1])
	print "Original bottom left data: ", bottomLeft
	print "Encoded bottom left data: ",  MapboxHeight2Height(outData[width-1, 0])
	print "Original bottom left data: ", bottomRight
	print "Encoded bottom right data: ",  MapboxHeight2Height(outData[width-1, height-1])
	print "Original center data: ", center
	print "Encoded center data: ",  MapboxHeight2Height(outData[(int(width/2)), (int(height/2))])

	saveFile(outData, outputFile)

if (1 != len(sys.argv)):
	demFile = sys.argv[1]
	outFile = sys.argv[2]

	generateImage(demFile, outFile)
else:
	print "Not enough parameters (demFile.tif outputFile.png)"