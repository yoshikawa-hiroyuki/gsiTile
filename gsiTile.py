#! /usr/bin/env python3
#
# gsiTile
#  (c)2017-2021 FUJITSU LIMITED
#
import sys, os
import math
import urllib.request, urllib.error
import numpy as np
from PIL import Image


class GSITile(object):
  """
  地理院タイルを取得し、合成してイメージファイルに保存する
  """
  tile_types = {
    'std': 'png',
    'pale': 'png',
    'blank': 'png',
    'english': 'png',
    'seamlessphoto': 'jpg'
  }
  

  def __init__(self, lat0, lat1, lon0, lon1, level=16,
               tile='seamlessphoto', tmpdir='tmp'):
    # zoomlevel
    self.tile_level = level

    # tile type
    self.tile_type = tile
    
    # working directory
    if os.path.exists(tmpdir) == False:
      os.makedirs(tmpdir)
    self.wkdir = tmpdir

    # get tile numbers
    if isinstance(lon0, list):
      dx1 = self.convertDeg(lon0)
    else:
      dx1 = lon0
    if isinstance(lon1, list):
      dx2 = self.convertDeg(lon1)
    else:
      dx2 = lon1
    if isinstance(lat0, list):
      dy1 = self.convertDeg(lat0)
    else:
      dy1 = lat0
    if isinstance(lat1, list):
      dy2 = self.convertDeg(lat1)
    else:
      dy2 = lat1
    self.origin = self.calcPixelCoord([dx1, dy1])
    self.sz = self.calcPixelCoord([dx2, dy2])
    self.sz[0] = self.sz[0] - self.origin[0]
    self.sz[1] = self.origin[1] - self.sz[1]
    
    # tile number & margin (pixel from the edge of tile)
    tx1, rx1 = self.calcLongitudeTileNum(dx1)
    tx2, rx2 = self.calcLongitudeTileNum(dx2)
    ty1, ry1 = self.calcLatitudeTileNum(dy1)
    ty2, ry2 = self.calcLatitudeTileNum(dy2)
    self.tileMin_x = tx1
    self.tileMin_xr = rx1
    self.tileMax_x = tx2
    self.tileMax_xr = rx2
    if tx1 > tx2 :
      self.tileMin_x = tx2
      self.tileMin_xr = rx2
      self.tileMax_x = tx1
      self.tileMax_xr = rx1
    self.tileMin_y = ty1
    self.tileMin_yr = ry1
    self.tileMax_y = ty2
    self.tileMax_yr = ry2
    if ty1 > ty2 :
      self.tileMin_y = ty2
      self.tileMin_yr = ry2
      self.tileMax_y = ty1
      self.tileMax_yr = ry1

    # get length per pixel
    self.leng = self.calcLengthPerPixel(lat=[dy1, dy2], long=[dx1, dx2])

  def __del__(self):
    pass

  def getPixelSize(self):
    sz =[self.tileMax_x-self.tileMin_x+1, self.tileMax_y-self.tileMin_y+1]
    sz[0] *= 256
    sz[1] *= 256
    return sz

  def convertDeg(self, d):
    deg = float(d[0]) + float(d[1])/60.0 + float(d[2])/3600.0
    return deg

  def calcLatitudeTileNum(self, deg):
    r1 = math.radians(deg)
    a1 = math.atanh(math.sin(r1))
    r2 = math.radians(85.05112878)
    a2 = math.atanh(math.sin(r2))
    y = 2**(self.tile_level +7)/math.pi*(-a1+a2)
    ty = y/256.0
    ry = y%256.0 + 0.5
    return int(ty), int(ry)

  def calcLongitudeTileNum(self, deg):
    x = 2**(self.tile_level +7)*(deg/180.0 +1)
    tx = x/256.0
    rx = x%256.0 + 0.5
    return int(tx), int(rx)

  def calcPixelCoord(self, deg):
    # longitude
    x = 2**(self.tile_level +7)*(deg[0]/180.0 +1)
    # latitude
    r1 = math.radians(deg[1])
    a1 = math.atanh(math.sin(r1))
    r2 = math.radians(85.05112878)
    a2 = math.atanh(math.sin(r2))
    y = 2**(self.tile_level +7)/math.pi*(-a1+a2)
    return [int(round(x)), int(round(y))]

  def calcLengthPerPixel(self, lat, long):
    r = 6378.137
    x1 = math.radians(long[0])
    x2 = math.radians(long[1])
    y1 = math.radians(lat[0])
    y2 = math.radians(lat[1])

    length = [0.0, 0.0]
    dx = x2 - x1
    s = math.sin(y1) * math.sin(y1)
    c = math.cos(y1) * math.cos(y1) * math.cos(dx)
    d = r * math.acos(s+c)
    length[0] = d * 1000.0 / self.sz[0]
    dx = x1 - x1
    s = math.sin(y1) * math.sin(y2)
    c = math.cos(y1) * math.cos(y2) * math.cos(dx)
    d = r * math.acos(s+c)
    length[1] = d * 1000.0 / self.sz[1]

    return length

  def getTiles(self):
    # URL format (level/longitude/latitude)
    url_fmt = "https://cyberjapandata.gsi.go.jp/xyz/%s/%d/%d/%d.%s"

    # download tiles
    numTile =(self.tileMax_x-self.tileMin_x+1)*(self.tileMax_y-self.tileMin_y+1)
    i = self.tileMin_x
    n_dl = 0
    sys.stderr.write('INFO: downloading map tile: %d / %d' % (n_dl, numTile))
    while ( i <= self.tileMax_x ):
      j = self.tileMin_y
      while ( j <= self.tileMax_y ):
        url = url_fmt % (self.tile_type, self.tile_level, i, j, \
                         GSITile.tile_types[self.tile_type])
        fname = "%d_%d.jpg" % (i, j)
        fname = os.path.join(self.wkdir, fname)

        dl_succeed = False
        xerr = 'something wrong.'
        for trial in range(10):
          try:
            r = urllib.request.urlopen(url=url)
            dl_succeed = True
            break
          except Exception as e:
            xerr = str(e)
            continue
          break
        if not dl_succeed:
          sys.stderr.write('error: %s\n' % xerr)
          sys.exit(-1)
        try:
          f = open(fname, "wb")
          f.write(r.read())
          f.close()
        except Exception as e:
          sys.stderr.write('error: %s\n' % str(e))
          sys.exit(-1)
        j += 1
        n_dl += 1
        sys.stderr.write('\rINFO: downloading map tile: %d / %d' % (n_dl, numTile))
      i += 1
    sys.stderr.write('\n')

  def mergeImage(self, crop=True):
    # merge all tiles and
    # returns merged image
    merge_sz = ((self.tileMax_x-self.tileMin_x+1)*256, \
                (self.tileMax_y-self.tileMin_y+1)*256)
    mgimg = Image.new('RGB', merge_sz)
    i = self.tileMin_x
    ii = 0
    while ( i <= self.tileMax_x ):
      j = self.tileMin_y
      jj = 0
      while ( j <= self.tileMax_y ):
        fname = "%d_%d.jpg" % (i, j)
        fname = os.path.join(self.wkdir, fname)
        img = Image.open(fname)
        mgimg.paste(img, (ii*256, jj*256))
        j += 1
        jj += 1
        continue # end of while(j)
      i += 1
      ii += 1
      continue # end of while(i)
    if crop:
      return self.cropImage(mgimg)
    return mgimg

  def cropImage(self, orgimg):
    # crop merged image by position and
    # returns croped image
    r = (self.tileMax_x - self.tileMin_x) * 256 + self.tileMax_xr
    xrange = [self.tileMin_xr, r]
    r = (self.tileMax_y - self.tileMin_y) * 256 + self.tileMax_yr
    yrange = [self.tileMin_yr, r]

    # crop merged image
    img = orgimg.crop((xrange[0], yrange[0], xrange[1], yrange[1]))
    return img

  def saveImage(self, img, fname):
    img.save(fname)

if __name__ == "__main__":
  level = 18
  #lat = [[35,40,6e-7], [35,44,59.999998921368004]]
  #lon = [[139,44,59.9999985618], [139,52,30.0000009]]
  lat = [36.639413033456435, 36.659306735128496]
  lon = [138.1776949697821, 138.19938069275926]
  pid = os.getpid()
  wkdir = os.path.join("..", "temp", str(pid))
  gsiTile = GSITile(lat[0], lat[1], lon[0], lon[1], level, wkdir)
  gsiTile.getTiles()
  img = gsiTile.mergeImage()
  gsiTile.saveImage(img, '{}.jpg'.format(pid))
  print(pid, 'done.')

