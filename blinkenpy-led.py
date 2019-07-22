#!/usr/bin/python3
################################################
#
# Setup of WS2801 device
#
################################################

import sys, os, re, time, argparse
from datetime import datetime
from array import array
import blinkentools as blt

debug = False

lut1Bit=[0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255]
lut2Bit=[0, 15, 41,255,255,255,255,255,255,255,255,255,255,255,255,255]
lut3Bit=[0,  4,  8, 15, 22, 41, 85,255,255,255,255,255,255,255,255,255]
lut4Bit=[0,  1,  2,  4,  6,  8, 11, 15, 19, 22, 30, 41, 58, 85,130,255]

################################################
#
# Setup of Led Tag
#
################################################

import usb.core

class ledNameTag ():
	"""Sets up the LED name tag."""

	def __init__(self):
		"""Define the LED name tag display provided by BerryBase (sertronic).
		USB vendor is 0x0416 and product id is 0x5020.
		The header is set with brightnes=25%, speeed=4 and mode=animation.
		"""

		self.vendor	= 0x0416
		self.product	= 0x5020
		self.height	= 11			# Rows of display
		self.width	= 44			# Columns of display
		self.charWidth	= 8			# Columns of a char
		self.dispChars	= (self.width+7)//8	# Display buffer has 48 pixel, but only 44 are shown

		self.device = usb.core.find(idVendor=self.vendor, idProduct=self.product)

		if self.device is None:
			print("No led tag with vendorID %04x and productID %04x found." % (self.vendor, self.product))
			print("Connect the led tag and run this tool as root.")
			sys.exit(1)
		if self.device.is_kernel_driver_active(0):
			self.device.detach_kernel_driver(0)
			self.device.set_configuration()

		print("using [%s %s] bus=%x dev=%x" % (self.device.manufacturer, self.device.product, self.device.bus, self.device.address))


		self.ioBuf =   [0x77, 0x61, 0x6e, 0x67, 0x00, 0x30, 0x00, 0x00, # 'wang' +0 + brightness( 30 =25 %)
				0x45, 0x45, 0x45, 0x45, 0x45, 0x45, 0x45, 0x45, # (slot 0-7) speed=4 and mode=animation
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # (slot 0-7) size of buffer
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
				0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
		self.ioSlot = 0

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

		missingBytes = self.height - (len(moviebuffer) % self.height)
		if missingBytes < self.height:
			moviebuffer.extend( (0,) * missingBytes)
		dm = len(moviebuffer) // self.height
		self.ioBuf[16+(2*self.ioSlot)] = dm // 256	#
		self.ioBuf[17+(2*self.ioSlot)] = dm % 256	#
		print ('Movie size        = %d bytes' % len(moviebuffer))

		self.ioBuf.extend(moviebuffer)
		self.ioSlot += 1
		return


	def checkSettings(self,movie):
		"""Checks the settings of the file and gives the user hints on how to make a better suited animation"""
		if(movie.width >  self.width):
			print( "Your animation is too wide. It will be cropped. Ideal width is %d pixels." % self.width)

		if(movie.width < self.width):
			print("Your animation is not wide enough. Part of the matrix will remain off. Ideal width is %d pixels." % self.width)

		if(movie.height > self.height):
			print("Your animation is too high. It will be cropped. Ideal height is %d pixels." % self.height)

		if(movie.height < self.height):
			print("Your animation is not high enough. Part of the matrix will remain off. Ideal height is %d pixels." % self.height)
		print ("")


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
		rows = self.height
		cols = self.dispChars

		mRows = movie.height
		mCols = movie.width

		print ("Display dimension = (%dx%d)" % (self.height , self.width))
		print ("Film dimension    = (%dx%d)" % (mRows , mCols))


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

			for col in range(cols):			# (x) 8 bit spalten
				for pixelRow in range (rows):	# (y) zeile
					byte_val = 0

					for bit in range(8):
						bit_val = 0
						pixelCol = 8*col+bit

						try:
							if  pixelCol >= mCols or pixelRow >= mRows :
								disp1 = disp2 = disp3 = '0'		# black
							elif movie.channels == 3 :
								disp1 = (frame.rows[pixelRow][(3*(pixelCol))+0])	# red / grey
								disp2 = (frame.rows[pixelRow][(3*(pixelCol))+1])	# green
								disp3 = (frame.rows[pixelRow][(3*(pixelCol))+2])	# blue
							else:
								disp1 = disp2 = disp3 = (frame.rows[pixelRow][pixelCol]) #

						except Exception as e:
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
							lx = (0,0,0)

						if sum(lx) > 0:
							bit_val = 1 << (7-bit)
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

		needpadding = len(buf)%64
		if needpadding:
			buf.extend( (0,) * (64-needpadding) )


		print ("IO buffer length  = %d byte(s)" % len(buf))
		if (len(buf)) > 8192:
			print ("IO buffer too big = %d bytes" % len(buf))
			print (buf[0:64])
			exit()
		else:
			print("Write ioBuf to USB device")
			for i in range(int(len(buf)/64)):
				time.sleep(0.01)
#				print( buf[i*64:i*64+64])
				self.device.write(1, buf[i*64:i*64+64])


if __name__ == "__main__":

#	x = 1<<4
#	print (x, end='')
#	print (' newline')
#	sys.exit()

	if (len(sys.argv) < 2):
		print ("You need to run this script with a filename. Example: 'blinkenpi-led.py test.bml'")
		print ("Anyway I will start a test.")
		filename = 'herz.bml'
#		sys.exit()

	elif (len(sys.argv) == 2):
		script, filename = sys.argv

	else:
		print ("Thats to many arguments. You need to run this script with one argument: the filename of the animation you want to play. Example: 'python blinkenpi.py test.bml'")
		sys.exit()

	blmDisplay = ledNameTag()

	bmlFilm = blt.blmMovie(filename)
	blmDisplay.checkSettings(bmlFilm)

	blmDisplay.createBuf(bmlFilm)

	blmDisplay.write()
