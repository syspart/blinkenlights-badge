#!/usr/bin/python3
################################################
#
# Run Blinkenlights movies on LED name badge
# https://www.berrybase.de/computer/pc-peripheriegeraete/usb-gadgets/led-name-tag-11x44-pixel-usb 
#
# links:
#
# https://github.com/jnweiger/led-name-badge-ls32
# https://github.com/DirkReiners/LEDBadgeProgrammer
# https://github.com/ghewgill/ledbadge
# bluetooth
# https://github.com/Nilhcem/ble-led-name-badge-android
# https://github.com/Doridian/ledbadge
# https://github.com/M4GNV5/BluetoothLEDBadge
#
################################################

import sys, os, re, time, argparse
from datetime import datetime
from array import array
import blinkentools as blt


################################################
#
# Lookup table to transcode gray shade movies to b/w movies
#
################################################

lut1Bit=[0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255]
lut2Bit=[0, 15, 41,255,255,255,255,255,255,255,255,255,255,255,255,255]
lut3Bit=[0,  4,  8, 15, 22, 41, 85,255,255,255,255,255,255,255,255,255]
lut4Bit=[0,  1,  2,  4,  6,  8, 11, 15, 19, 22, 30, 41, 58, 85,130,255]

################################################
#
# Setup of LED badge
#
################################################

import usb.core

class ledNameTag ():
	"""Sets up the LED name badge."""

	def __init__(self):
		"""Define the LED name tag display provided by BerryBase (sertronic).
		USB vendor is 0x0416 and product id is 0x5020.
		The dimension is 48x11 pixel, only 44x11 are shown.
		The header is set width brightnes=25%, speeed=4 and mode=animation.
		"""

		self.vendor	= 0x0416
		self.product	= 0x5020
		self.dRows	= 11			# Rows of display
		self.dCols	= 44			# Columns of display
		self.fCols	= 48			# Columns of frame
		self.bCols	= 8			# Columns of a buffer
		self.fBuffers	= (self.fCols+(self.bCols)-1)//self.bCols	# Display buffer has 48 pixel, but only 44 are shown

		self.device = usb.core.find(idVendor=self.vendor, idProduct=self.product)

		if self.device is None:
			print("No led tag with vendorID %04x and productID %04x found." % (self.vendor, self.product))
			print("Connect the led tag and run this tool as root.")
			sys.exit(1)
		if self.device.is_kernel_driver_active(0):
			self.device.detach_kernel_driver(0)
			self.device.set_configuration()

		print("using [%s %s] bus=%x dev=%x" % (self.device.manufacturer, self.device.product, self.device.bus, self.device.address))

		self.ioSlot = 0
		self.ioBuf =   [0x77, 0x61, 0x6e, 0x67, 0x00, 0x30, 0x00, 0x00, # 'wang' +0 + brightness( 30 =25 %)
				0x15, 0x15, 0x45, 0x45, 0x45, 0x45, 0x45, 0x45, # (slot 0-7) speed=4 and mode=animation
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # (slot 0-7) size of buffer
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
# Brightness
		br = 3	# 3 = 25%, 2 = 50%, 1=75%, 0 =100%
		self.ioBuf[5] = (br & 3)<< 4


# Timestamp
		cdate = datetime.now()
		self.ioBuf[38+0] = cdate.year % 100
		self.ioBuf[38+1] = cdate.month
		self.ioBuf[38+2] = cdate.day
		self.ioBuf[38+3] = cdate.hour
		self.ioBuf[38+4] = cdate.minute
		self.ioBuf[38+5] = cdate.second


	def fillSlot(self,moviebuffer, speed):
		"""Set 8 message slots.
		Moviebuffer must be multible of byte*height.
		"""

		if self.ioSlot > 7:
			print ("Too much slots")
			quit()

		self.ioBuf[8+self.ioSlot] = ((speed & 7) << 4) + 5	# speed + "animation"

		missingBytes = self.dRows - (len(moviebuffer) % self.dRows)
		if missingBytes < self.dRows:
			moviebuffer.extend( (0,) * missingBytes)
		dm = len(moviebuffer) // self.dRows
		self.ioBuf[16+(2*self.ioSlot)] = dm // 256	#
		self.ioBuf[17+(2*self.ioSlot)] = dm % 256	#
		print ('Movie size        = %d bytes' % len(moviebuffer))

		self.ioBuf.extend(moviebuffer)
		self.ioSlot += 1
		return

	def createBuf(self,movie):
		""" Create an LED buffer for a LED tag.
		Movie has pixel, so add 8 of them them to a byte.
		"""

		clr  = ( 255, 255, 255)		# Base intensity of one pixel (RBG)
		if    movie.bits == 2:		# Select lookup table for color and intensity transformation
			lutBit = lut2Bit
		elif  movie.bits == 3:
			lutBit = lut3Bit
		elif  movie.bits == 4:
			lutBit = lut4Bit
		else:
			lutBit = lut1Bit

		buf = []

		mRows = movie.height
		mCols = movie.width

		print ("Display dimension = (%dx%d)" % (self.dCols,self.dRows))
		print ("Film dimension    = (%dx%d)" % (mCols, mRows))

		frmCnt = 0					# we need a frame counte, because the size of a buffer may not exeed 255 clounms => 31 frames
		for frame in movie.frames:
			frmCnt += 1
			if frmCnt == 1:
				xtime = float(frame.time) / 1000.0
				if xtime <= 0.066:
					sleeptime = 7
				elif xtime <= 0.133:
					sleeptime = 6
				elif xtime <= 0.222:
					sleeptime = 5
				elif xtime <= 0.357:
					sleeptime = 4
				elif xtime <= 0.416:
					sleeptime = 3
				elif xtime <= 0.5:
					sleeptime = 2
				elif xtime <= 0.769:
					sleeptime = 1
				else: 	sleeptime = 0

				print ("Sleeptime         = %d" % sleeptime)

			for fBuffer in range(self.fBuffers):
				for pixelRow in range (self.dRows):
					byte_val = 0

					for bCol in range(self.bCols):
						bit_val = 0
						pixelCol = self.bCols*fBuffer+bCol			# Real pixel of movie

						try:
							if  pixelCol >= mCols or pixelRow >= mRows :	# out of range
								disp1 = disp2 = disp3 = '0'		# black
							elif movie.channels == 3 :			# we have 3 colors
								disp1 = (frame.rows[pixelRow][(3*(pixelCol))+0])	# red
								disp2 = (frame.rows[pixelRow][(3*(pixelCol))+1])	# green
								disp3 = (frame.rows[pixelRow][(3*(pixelCol))+2])	# blue
							else:
								disp1 = disp2 = disp3 = (frame.rows[pixelRow][pixelCol]) # grey

						except Exception as e:				# every other convert error
							disp1 = disp2 = disp3 = '0'		# black

						if movie.channels == 3:
							multR = lutBit[blt.alpha2num(disp1)]
							multG = lutBit[blt.alpha2num(disp2)]
							multB = lutBit[blt.alpha2num(disp3)]
						else:
							multR = multG = multB = lutBit[blt.alpha2num(disp1)]

						if (movie.channels == 1 or movie.channels == 3):
							lx = ((clr[0]*multR)/255,(clr[1]*multB)/255,(clr[2]*multG)/255)

						else:
							lx = (0,0,0)				# not found so it is blak

						if sum(lx) > 0:
							bit_val = 1 << (7-bCol)
						byte_val += bit_val

					buf.append(byte_val)

			if frmCnt >= 123:	# 123 frames * 6 * 11 bytes are max lenght!
				break
		if frmCnt > 0:
			self.fillSlot(buf,sleeptime)
		print ('Film length       = %d frames' % (frmCnt))
		return


	def write(self):
		buf = array('B')
		buf.extend(self.ioBuf)

		print ("IO buffer length  = %d byte(s)" % len(buf))
		if (len(buf)) > 8192:
			print ("IO buffer too big = %d bytes" % len(buf))
			exit()
		else:
			print("Write ioBuf to USB device")
			self.device.write(1, buf,1000)

if __name__ == "__main__":

	blmDisplay = ledNameTag()

	if (len(sys.argv) < 2):
		print ("You need to run this script with a filename. Example: 'blinkenpi-led.py test.bml'")
		print ("Anyway I will start a test.")
		filename = 'herz.bml'
		bmlFilm = blt.blmMovie(filename)
		blmDisplay.createBuf(bmlFilm)

	elif (len(sys.argv) < 7):

		for i in range (1,len(sys.argv)):
			filename = sys.argv[i]
			bmlFilm = blt.blmMovie(filename)
			blmDisplay.createBuf(bmlFilm)

	else:
		print ("Thats to many arguments. You need to run this script with one argument: the filename of the animation you want to play. Example: 'python blinkenpi.py test.bml'")
		sys.exit()


	blmDisplay.write()
