#!/usr/bin/python
#################################################
#
#
import xml.etree.ElementTree as ET
#
#
class blmFrame(object):
	"""A Frame with indivdual rows as used in the blm file."""

	def __init__(self):
		self.rows = []
		self.time = 0
		self.number_rows = 0

	def addrow(self, toadd):
		self.rows.append(toadd)
		self.number_rows = self.number_rows + 1
#
class blmMovie(object):
	"""Class for an Blinkenlight film."""

	def addframe(self, toadd):
		self.frames.append(toadd)
		self.length = self.length + 1

	def __init__(self,file):
		self.frames	= []
		self.height	= 0
		self.width	= 0
		self.length	= 0
		self.loop	= False
		self.bits	= 0
		self.channels	= 0

		document = ET.parse(file)
		animation = document.getroot()

		if(animation.tag != 'blm'):
			print ("Sorry, can't find blm root. Looks like this is not a valid blinkenmovie file")
			sys.exit()

		# get settings from the attributes of the root tag
		try:
			self.loop = animation.find('header').find('loop').text = "Yes"
		except:
			self.loop = False

		# 1 to 4 bits ara supported.
		try:
			self.bits = int(animation.attrib['bits'])
		except:
			self.bits = 1
		finally:
			if (self.bits < 1 or self.bits>4):
				print (str(self.bits)+' bit(s) are not supported')
				quit()

		# only 1 2, 3 channels ara supported
		try:
			self.channels = int(animation.attrib['channels'])
		except:
			self.channels = 1
		finally:
			if (self.channels < 1 or self.channels>3):
				print (str(self.bits)+' channel(s) are not supported')
				quit()

		try:
			self.height = int(animation.attrib['height'])
		except:
			print ('No height are set')
			quit()

		try:
			self.width = int(animation.attrib['width'])
		except:
			print ('No width are set')
			quit()

		# go through all the frames and all the in each frame and add them to the Movie object
		for frame in animation.findall('frame'):
			f = blmFrame()
			for row in frame.findall('row'):
				f.addrow(row.text)
			f.time = frame.attrib['duration']
			self.addframe(f)


def bitmap_img(movie):
	""" returns a tuple of (buffer, length_in_byte_columns)
	"""
	buf = array('B')
	cols = (movie.width+7)/8
	for col in range(cols):
		for row in range(11):
			byte_val = 0
			for bit in range(8):
				bit_val = 0
				x = 8*col+bit
				if x < im.width and sum(im.getpixel( (x, row) )) > 384:
					bit_val = 1 << (7-bit)
				byte_val += bit_val

			buf.append(byte_val)
	return (buf, cols)


def alpha2num(hstr):
        alpha = hstr.lower()
        if  alpha in '1':
                return 1
        elif alpha in '2':
                return 2
        elif alpha in '2':
                return 2
        elif alpha in '3':
                return 3
        elif alpha in '4':
                return 4
        elif alpha in '5':
                return 5
        elif alpha in '6':
                return 6
        elif alpha in '7':
                return 7
        elif alpha in '8':
                return 8
        elif alpha in '9':
                return 9
        elif alpha in 'a':
                return 10
        elif alpha in 'b':
                return 11
        elif alpha in 'c':
                return 12
        elif alpha in 'd':
                return 13
        elif alpha in 'e':
                return 14
        elif alpha in 'f':
                return 15
        return 0


