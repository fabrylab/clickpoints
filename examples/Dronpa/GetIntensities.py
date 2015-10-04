
from __future__ import division
from pylab import *
from skimage.measure import find_contours
import os

########### Parameters ##################

# Which directory?
folder = os.path.dirname(sys.argv[1])
os.chdir(folder)
# How are the images named?
filename = "1-%dmin.tif"
# How are the masks named?
mask_name = "1-%dmin_mask.png"

# What are the times used?
times = [0.,2,4,6,8,10]

# What colors should be used for plotting
colors = ['k',[0,0,1],[0,0.2,0.8],[0,0.8,0],[0,0.6,0.2],[0.8,0,0],[0.6,0.2,0],  [0.2,0,1],[0.2,0,0.8]]
# What linestyles should be used for plotting
styles = ['-','-','-','-','-','-','-','-','-','--','-','--','--','--']

#########################################

def stderr(values):
    return std(values)/sqrt(len(values))

def bootstrap(values):
    values = values.ravel()
    count = 10
    means = zeros(count)
    for i in xrange(count):
        indices = randint(0, len(values), len(values))
        means[i] = mean(values[indices])
    return std(means)

inte_list2 = []
error_list2= []
error_list2B= []
sizes = []
N = 7
for m in xrange(N):
    inte_list = []
    error_list = []
    print "---------------------",m
    for t in times:
        mask1 = (imread(mask_name%t)*255).astype(uint8)
        mask = mask1==(m+1)
        im1 = imread(filename%t)[:,:,1]
        inte_list.append(mean(im1[mask]))
        error_list.append(bootstrap(im1[mask]))
        error_list2B.append(stderr(im1[mask]))
        print sum(mask)
        if t == times[0]:
            sizes.append(sum(mask))

    inte_list2.append(array(inte_list))
    error_list2.append(array(error_list))

figure(0, (15,6))
subplot(121)
for m in xrange(N):
    errorbar(times, inte_list2[m]*sizes[m]-inte_list2[-1]*0, error_list2[m], color=colors[m], linestyle=styles[m])

xlim(-0.5,10.5)

xlabel("time (min)")
ylabel("intensitiy")

subplot(122)
t = 2

im1 = imread(filename%t)
imshow(im1)

minx = im1.shape[1]
maxx = 0
miny = im1.shape[0]
maxy = 0
centers = []
for m in xrange(N):
    mask1 = (imread(mask_name%t)*255).astype(uint8)
    mask = mask1==(m+1)
    line = find_contours(mask, 0.5)
    plot(line[0][:,1], line[0][:,0], color=colors[m])

    centers.append([mean(line[0][:,1]), mean(line[0][:,0])])
    text(mean(line[0][:,1]), mean(line[0][:,0]), m, va="center", ha="center", color="w")
    minx = min([minx, min(line[0][:,1])])
    maxx = max([maxx, max(line[0][:,1])])
    miny = min([miny, min(line[0][:,0])])
    maxy = max([maxy, max(line[0][:,0])])
print maxx
xlim(minx-0.5*(maxx-minx),maxx+0.5*(maxx-minx))
ylim(maxy+0.5*(maxy-miny),miny-0.5*(maxy-miny))
savefig("Intensities.png")
savetxt("cell.txt", concatenate((array([times]), inte_list2)).T)
savetxt("cell_sizes.txt", sizes)
savetxt("cell_centers.txt", centers)
show()