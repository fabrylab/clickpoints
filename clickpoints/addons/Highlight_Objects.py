#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Highlight_Objects.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

""" Highlight objects: Programm to mark a clicked region. In clickpoints put a marker on several regions you want to highlight. Then start this script
Optionally a gui opens, where you can set up some parameter and then a mask is created that (ideally) is identically to each region, on which a marker was placed.
How does it work: The program divides the picture in superpixels  (size adjustable by input parameters) and then divides these superpixels in
 an adjustable number of groups by a k-means-clustering algorithm. The Parameters used for the clustering of the superpixels differ
 but may be something like their mean luminescence in all colors. Then all superpixels belonging to the same cluster AND being connected
 are grouped in one region. If one (ore more) markers were set on this region it is highlighted. A mask is created, which contains all highlighted
 regions.
Programm created by Jakob. For any problems ask me or write an email to Jakob.Peschel@fau.de
"""



from __future__ import division, print_function
import numpy as np
import matplotlib.pyplot as plt
import skimage.measure
import skimage.segmentation
import sklearn.cluster
import skimage.color
import os, sys
import scipy.ndimage.filters
import distutils.util
import scipy as scp

#region import QT-Widget for Gui
try:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QIcon, QCheckBox,QDoubleSpinBox
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QIcon, QCheckBox,QDoubleSpinBox
    from PyQt4.QtCore import Qt

icon_path = os.path.join(os.path.dirname(__file__), "icons")

#endregion

class image_segmenter():
    def __init__(self, image, coords, mean_pixel_size=200, k_mean_cluster_number=5, compactness=24, iterations=10, enforced_connectivity=True, min_size=0.4,
                 verbose=True, k_means_cluster_mode=1, colorspace=1, ratio_sobel_image=0.3, connect_first=True,
                 histogram_bins=3, create_all_images=False, just_super_pixel_segmentation_im=False,
                 create_mean_col_regions=False, clickpoints_addon=True, already_given_regions=[], already_give_regions=False, highlight_whole_cluster=False,
                 wiener_filter = False, grad_just_lum_im = False, grad_sqrt = True,
                 wiener_filter_size = None, gradient_exponent = 0.5):
        """
        Init

        :param int8 RGB image: input image
        :param nx2 int list coords:  Coordinates of the markers
        :param int mean_pixel_size: Mean Size of a superpixel
        :param Bool highlight_whole_cluster: Whole cluster not just clicked region is highlighted if True
        :param double compactness: compactness used for superpixelization (also look in Docu of slic-algorithm)
        :param int iterations: maximum number of iterations for superpixelization (also look in Docu of slic-algorithm)
        :param Bool enforced_connectivity: Enforces Connectivity of the superpixelization for superpixels (also look in Docu of slic-algorithm)
        :param double min_size: Minimum size of a superpixel compared to the average size (also look in Docu of slic-algorithm)
        :param int k_mean_cluster_number: number of Clusters for k-means algorithm
        :param Bool just_super_pixel_segmentation_im: If True stop after superpixelization and return superpixel-boarder-marked image
        :param Bool verbose: If False nothing is printed out during method
        :param int 1|2 k_means_cluster_mode: Parameter for k-means-clustering of the superpixels 1==Mean of Superpixels in all 3 self.colors in lab-space 2==Clustering of the Histogram of the superpixels in all three self.colors in lab-space
        :param Bool already_give_regions: Just for Debugging It is possible to give the final connected regions (a labeled image) and the highlight, which is clicked.
        :param image labels already_given_regions: Just for Debugging see already_give_regions
        :param int histogram_bins: Number of Histogram bins if k_means cluster mode==2
        :param Bool create_all_images: Create and return everything if True
        :param clickpoints_addon: Just for Debugging Not important for user
        :param create_mean_col_regions: Picture of Mean of Luminescence is created. Just to visualize how strong the mean-col clustering is
        :return:
        """
        self.verbose=verbose

        if image.shape[2]>3:
            image=image[:,:,0:3]

        self.image=image
        self.superpixel_segmentation_labels=[]
        self.mean_regions_col=[]
        self.props_col=[]
        self.regions_for_mask=[]


        # if(self.image.max())<=1:
        #     self.image =int(self.image * 255)


        #region choose colorspace


        ##creation of image in I1I2I3 colorspace
        # self.I1I2I3_im=np.zeros(self.image.shape)
        # self.I1I2I3_im[:,:,0]=(self.image[:,:,0]+self.image[:,:,1]+self.image[:,:,2])/3
        # self.I1I2I3_im[:,:,1]=(self.image[:,:,0]-self.image[:,:,2])/2
        # self.I1I2I3_im[:,:,2]=(2*self.image[:,:,1]-self.image[:,:,0]-self.image[:,:,2])/4
        #
        # plt.subplot(2,3,1)
        # plt.imshow(self.I1I2I3_im[:,:,0])
        # plt.subplot(2,3,2)
        # plt.imshow(self.I1I2I3_im[:,:,1])
        # plt.subplot(2,3,3)
        # plt.imshow(self.I1I2I3_im[:,:,2])
        # plt.subplot(2,3,4)
        # plt.imshow(self.im_lab[:,:,0])
        # plt.subplot(2,3,5)
        # plt.imshow(self.im_lab[:,:,1])
        # plt.subplot(2,3,6)
        # plt.imshow(self.im_lab[:,:,2])
        # plt.show()
        #use_I1I2I3=True

    #region colorspaces
        if self.image.shape[2]==3:
            if(colorspace == 1):
                self.im_lab=skimage.color.rgb2lab(self.image)
                self.im_color_space=self.im_lab
            if(colorspace == 2):
                self.I1I2I3_im=np.zeros(self.image.shape)
                self.I1I2I3_im[:,:,0]=(self.image[:,:,0]+self.image[:,:,1]+self.image[:,:,2])/3
                self.I1I2I3_im[:,:,1]=(self.image[:,:,0]-self.image[:,:,2])/2
                self.I1I2I3_im[:,:,2]=(2*self.image[:,:,1]-self.image[:,:,0]-self.image[:,:,2])/4
                self.im_color_space=self.I1I2I3_im
            if colorspace == 3:
                self.im_color_space=skimage.color.rgb2grey(self.image)
                self.im_color_space=self.im_color_space.reshape((self.im_color_space.shape[0],self.im_color_space.shape[1],1))
                self.colors=1
        else: # set colorspace to grey_image if got greyimage
            colorspace=3
            self.im_color_space=self.image
        if verbose:
            print('image transformed in correct colorspace')

#endregion

# region Wiener Filter
        if wiener_filter:
            self.im_color_space_not_wiener = np.copy(self.im_color_space)
            for i in range(self.im_color_space.shape[2]):
                self.im_color_space[:,:,i] = scp.signal.wiener(self.im_color_space[:,:,i],mysize=wiener_filter_size)
            # plt.figure(19)
            # plt.imshow(self.im_color_space_not_wiener[:,:,0])
            # plt.figure(20)
            # plt.imshow(self.im_color_space[:,:,0])
            # plt.show()
            if verbose:
                print('Applied Wiener Filer')
# endregion
        ax1=plt.subplot(1,2,1)
        ax=plt.imshow(self.im_color_space_not_wiener[:,:,0],cmap= 'Greys_r')
        plt.title('Original')
        plt.subplot(1,2,2,sharex = ax1,sharey = ax1)
        plt.imshow(self.im_color_space[:,:,0],cmap= 'Greys_r')
        plt.title('Filtered')
        plt.show()


        if(self.im_color_space.max())<=1:
            self.im_color_space *= 255

        self.ratio_sobel_image=ratio_sobel_image
        if self.ratio_sobel_image>0:
            #create sobel image
            if grad_just_lum_im:
                sobel_image_x=np.asarray(scipy.ndimage.filters.sobel(self.im_color_space[:,:,0],axis=1),dtype=float)
                sobel_image_y=np.asarray(scipy.ndimage.filters.sobel(self.im_color_space[:,:,0],axis=0),dtype=float)
                self.sobel_im=np.sqrt(((sobel_image_x) ** 2) + ((sobel_image_y) ** 2) )
                self.sobel_im=self.sobel_im.reshape((self.sobel_im.shape[0],self.sobel_im.shape[1],1))
            else:
                sobel_image_x=np.asarray(scipy.ndimage.filters.sobel(self.im_color_space,axis=1),dtype=float)
                sobel_image_y=np.asarray(scipy.ndimage.filters.sobel(self.im_color_space,axis=0),dtype=float)
                self.sobel_im=np.sqrt(((sobel_image_x) ** 2) + ((sobel_image_y) ** 2) )


            if grad_sqrt:
                self.sobel_im = self.sobel_im ** gradient_exponent
                # self.sobel_im = self.sobel_im ** 200
            #normalize sobel image
            # self.sobel_im = self.sobel_im - self.sobel_im.min()
            # self.sobel_im = self.sobel_im / self.sobel_im.max()


            self.sobel_im=self.sobel_im*(self.im_color_space.mean()/self.sobel_im.mean())

            #put image and sobeled_image in one image which is then treated as an image with twice the number of colors as the original image
            if self.ratio_sobel_image<1:
                new_im=np.zeros((self.im_color_space.shape[0],self.im_color_space.shape[1],self.im_color_space.shape[2]+self.sobel_im.shape[2]),np.float)
                new_im[:,:,0:self.im_color_space.shape[2]]=self.im_color_space*(1 - self.ratio_sobel_image)
                new_im[:,:,self.im_color_space.shape[2]:self.im_color_space.shape[2]+self.sobel_im.shape[2]]= self.sobel_im * self.ratio_sobel_image
                self.im_color_space=new_im
            #exchange im with sobel image
            else:
                self.im_color_space=self.sobel_im
            self.colors=self.im_color_space.shape[2]
            if self.verbose:
                print('Sobeled image created')




        # sobel_im_x=scipy.ndimage.filters.sobel(im,axis=1)
        # sobel_im_x=np.asarray(sobel_im_x,dtype=float)
        # sobel_im_y=scipy.ndimage.filters.sobel(im,axis=0)
        # sobel_im_y=np.asarray(sobel_im_y,dtype=float)
        # sobel_im_sqare=((sobel_im_x+sobel_im_y)**2)
        # sobel_im_sqare=sobel_im_sqare/sobel_im_sqare.max()
        # sobel_im_abs=(np.abs(sobel_im_x+sobel_im_y))
        # sobel_im_abs=sobel_im_abs/sobel_im_abs.max()

        #endregion
        if (len(coords)) == 0:
            print('Error got no Coordinates')
            return

        if already_give_regions:
            self.regions_for_mask = already_given_regions
        else:
            # region superpixelization
            number_of_superpixels = int(np.shape(self.image)[0] * np.shape(self.image)[1] / mean_pixel_size)
            # im_l_b_grad = self.im_color_space[:,:,0:3]
            # im_l_b_grad[:,:,1] = self.im_color_space[:,:,3]
            self.superpixel_segmentation_labels = skimage.segmentation.slic(self.image, n_segments=number_of_superpixels, compactness=compactness,
                                                                            multichannel=True, max_iter=10,
                                                                            enforce_connectivity=enforced_connectivity,
                                                                            min_size_factor=min_size)  # segmentiert in regions
            # plt.figure(19)
            # plt.imshow(im_l_b_grad[:,:,0])
            # plt.figure(20)
            # plt.imshow(im_l_b_grad[:,:,1])
            # plt.figure(21)
            # plt.imshow(im_l_b_grad[:,:,2])


            # self.superpixel_segmentation_labels = skimage.segmentation.slic(im_l_b_grad, n_segments=number_of_superpixels, compactness=compactness,
            #                                                     multichannel=True, max_iter=10,
            #                                                     enforce_connectivity=enforced_connectivity,
            #                                                     min_size_factor=min_size,convert2lab = False)  # segmentiert in regions
            if self.verbose:
                print('superpixelization done')
            # endregion

            # region k_means_clustering
            self.colors = self.im_color_space.shape[2]
            if k_means_cluster_mode == 1:
                self.k_mean_clustered_regions = np.zeros((np.shape(self.image)[0], np.shape(self.image)[1]), int)

                #create 3xregionprops(image) for each color of image

                for i in range(self.colors):
                    self.props_col.append(skimage.measure.regionprops(self.superpixel_segmentation_labels, self.im_color_space[:, :, i]))

                if self.verbose:
                    print('Created regionprops')

                #create list with shape number_of_superpixels x number_of_colors with mean of every superpixel in every color
                means_col = np.zeros(np.shape(self.props_col), float)
                for row in range(means_col.shape[0]):
                    for column in range(means_col.shape[1]):
                        means_col[row][column] = self.props_col[row][column].mean_intensity

                #actual k-means-clustering
                kmeans_col = sklearn.cluster.KMeans(k_mean_cluster_number)
                means_col = means_col.transpose()
                cluster_labels_col = kmeans_col.fit_predict(means_col)

                # create labeled image
                for row in range(np.shape(self.image)[0]):
                    for column in range(np.shape(self.image)[1]):
                        self.k_mean_clustered_regions[row, column] = cluster_labels_col[self.superpixel_segmentation_labels[row, column] - 1]  # Regionen nach kmeans-Clustering
                    if row % 50 == 0 and self.verbose:
                        print('Creating Clustered Image row=%i Processed Percentage %i' % (row, 100 * row / np.shape(self.image)[0]))

                if self.verbose:
                    print('clustering done')
            # endregion


            #region histogram_clustering
            if (k_means_cluster_mode == 2):
                self.k_mean_clustered_regions = np.zeros((np.shape(self.image)[0], np.shape(self.image)[1]), int)

                #region create histograms for each superpixel
                self.histogramms = []
                for num_superpixel in range(np.max(self.superpixel_segmentation_labels) + 1):
                    local_superpixel = self.im_color_space[self.superpixel_segmentation_labels == num_superpixel]
                    local_hist = np.zeros((self.colors, histogram_bins), float)
                    for color in range(self.colors):
                        local_hist[color, :], _ = np.histogram(local_superpixel[:,color],range=(0,255), bins=histogram_bins, density=True)
                    local_hist = local_hist.reshape(histogram_bins * self.colors)
                    local_hist /= sum(local_hist)
                    self.histogramms.append(local_hist)
                    if num_superpixel % 1000 == 0 & self.verbose:
                        print('%i histograms of superpixels created. Processed Percentage %i' % (
                        num_superpixel, 100 * num_superpixel / np.max(self.superpixel_segmentation_labels)))
                    # if num_superpixel%1000==0:
                    #     plt.figure(1)
                    #     plt.plot(range(histogram_bins),local_hist)
                    #     plt.figure(2)
                    #     plt.imshow(skimage.segmentation.mark_boundaries(self.image, np.asarray(self.superpixel_segmentation_labels == num_superpixel,dtype=int)))
                    #     plt.show()

                #endregion

                #actual kmeans clustering
                k_means_hist = sklearn.cluster.KMeans(k_mean_cluster_number)
                cluster_labels_col = k_means_hist.fit_predict(self.histogramms)
                #endregion

                #region create image with cluster labels
                for row in range(np.shape(self.image)[0]):
                    for column in range(np.shape(self.image)[1]):
                        self.k_mean_clustered_regions[row, column] = cluster_labels_col[
                            self.superpixel_segmentation_labels[row, column] - 1]  # Regionen nach kmean-Clustering

                    if row % 50 == 0 & self.verbose:
                        print('Creating image with cluster labels row=%i Processed Percentage %i' % (
                        row, 100 * row / np.shape(self.image)[0]))
                #endregion

                if self.verbose:
                    print('clustering done')



            # region merge clicked clusters
            if connect_first:
            # region merge clicked clusters
                label_list=[]
                for coord in coords:
                    region_label=self.k_mean_clustered_regions[coord[1],coord[0]]
                    already_used=False
                    for label in label_list:
                        if label==region_label:
                            already_used=True
                    if not already_used:
                        label_list.append(region_label)

                # endregion
                self.mask_clicked_clusters=(self.k_mean_clustered_regions==label_list[0])
                for label in label_list[1:]:
                    self.mask_clicked_clusters=self.mask_clicked_clusters|(self.k_mean_clustered_regions==label)
                if self.verbose:
                    print('label list=',label_list)
                    print('Merging clicked clusters done')
            # endregion
            if False:
                a=3


    #region create connected regions
            if highlight_whole_cluster:
                self.regions_for_mask = self.k_mean_clustered_regions
            else:
                if connect_first:
                    self.regions_for_mask=skimage.measure.label(self.mask_clicked_clusters)
                else:
                    self.regions_for_mask = skimage.measure.label(self.k_mean_clustered_regions)
            if self.verbose:
                print('connected_regions done')

    #endregion


        #region extract marked regions from marker positions (coords) to pointed regions,a region which is marked more than once is just one time in pointed regions
        pointed_regions = []
        for coord in coords:
            pointed_region = self.regions_for_mask[coord[1], coord[0]]
            already_marked = False
            for used_regions in pointed_regions:
                if (used_regions == pointed_region):
                    already_marked = True
            if (~already_marked):
                pointed_regions.append(pointed_region)
        if (self.verbose):
            print('clicked coordinates are')
            print(coords)
            print('pointed_regions=' % (pointed_regions))

        #endregion

        #region create mask_one_region for each pointed_region and OR the masks_one_region
        masks_one_region = []
        for pointed_region in pointed_regions:
            mask_one_region = pointed_region == self.regions_for_mask
            if not clickpoints_addon:
                mask_one_region = np.reshape(mask_one_region, (mask_one_region.shape[0], mask_one_region.shape[1], 1))
            masks_one_region.append(mask_one_region)

        if not clickpoints_addon:
            self.mask = np.zeros([self.image.shape[0], self.image.shape[1], 1], np.uint8)
        else:
            self.mask = np.zeros([self.image.shape[0], self.image.shape[1]], np.uint8)
        for mask_one_region in masks_one_region:
            self.mask = self.mask | mask_one_region
        # # filling holes in mask
        # self.mask=scipy.ndimage.morphology.binary_fill_holes(self.mask)
        if self.verbose:
            print('creating mask done')
        #endregion

        if create_all_images:
            self.get_mean_regions_col = None
            self.get_super_pixel_marked_image()
            self.get_connected_regions_marked_boarders_image()


    #creates mean of superpixel for each color in lab-space
    def get_mean_regions(self):
        self.mean_regions_col = np.zeros((np.shape(self.im_color_space)), float)
        # if self.colors>3:
        #     colors_for_mean_image=3
        # elif self.colors==2:
        #     colors_for_mean_image=1
        # else:
        #     colors_for_mean_image=self.colors
        for color in range(self.colors):
            for row in range(self.mean_regions_col.shape[0]):
                for column in range(self.mean_regions_col.shape[1]):
                    self.mean_regions_col[row, column, color] = self.props_col[color][self.superpixel_segmentation_labels[row, column]-1].mean_intensity
                if row % 50 == 0 & self.verbose :
                    print('row=%i color=%i Processed Percentage %i Creating Mean Image' % (row,color,100 * row / np.shape(self.image)[0]))


    def get_super_pixel_marked_image(self):
        self.super_pixel_image = skimage.segmentation.mark_boundaries(self.image, self.superpixel_segmentation_labels)


    def get_connected_regions_marked_boarders_image(self):
        self.connected_regions_marked_boarders_image=skimage.segmentation.mark_boundaries(self.image, self.regions_for_mask)




class Param_Delivery(QWidget):
    def __init__(self):
        # self.super_pixel_size
        # self.cluster_number

        # region initialization
        application_canceled=False
        self.just_superpixelization=False
        self.return_just_mask=True

        # self.file=open('Highlight_objects_config_file.dat','w+')
        # self.file.close()
        opened_existing_file=False
        try:
            self.file=open('ConfigHighlightObjects.txt','r+')
            opened_existing_file=True
        except IOError:
            print('Config-File does not exist. Created new config file')
            self.file=open('ConfigHighlightObjects.txt','w')
            opened_existing_file=False



        #endregion

        #region read parameters from file
        if opened_existing_file:
            parameter_string=self.file.read()
            for arg in parameter_string.split("\n"):
                # print(arg)
                if arg.startswith('super_pixel_size='):
                    self.super_pixel_size=int(arg.replace('super_pixel_size=',''))
                    #print('found superpixelsize', int(super_pixel_size))
                if arg.startswith('cluster_number='):
                    self.cluster_number=int(arg.replace('cluster_number=',''))
                if arg.startswith('k_means_cluster_mode='):
                    self.k_means_cluster_mode=int(arg.replace('k_means_cluster_mode=',''))
                if arg.startswith('histogram_bins='):
                    self.histogram_bins=int(arg.replace('histogram_bins=',''))
                if arg.startswith('colorspace='):
                    self.colorspace=int(arg.replace('colorspace=',''))
                if arg.startswith('open_gui='):
                    self.open_gui=distutils.util.strtobool(arg.replace('open_gui=',''))
                if arg.startswith('ratio_sobel_image='):
                    self.ratio_sobel_image=float(arg.replace('ratio_sobel_image=',''))
                if arg.startswith('show_super_pixel_image='):
                    self.show_super_pixel_image=distutils.util.strtobool(arg.replace('show_super_pixel_image=',''))
                if arg.startswith('show_k_clustered_image='):
                    self.show_k_clustered_image=distutils.util.strtobool(arg.replace('show_k_clustered_image=',''))
                if arg.startswith('show_border_image='):
                    self.show_border_image=distutils.util.strtobool(arg.replace('show_border_image=', ''))
                if arg.startswith('show_mask='):
                    self.show_mask=distutils.util.strtobool(arg.replace('show_mask=',''))
                if arg.startswith('show_mean_image='):
                    self.show_mean_image=distutils.util.strtobool(arg.replace('show_mean_image=',''))
                if arg.startswith('show_sobel_image='):
                    self.show_sobel_image=distutils.util.strtobool(arg.replace('show_sobel_image=',''))
                if arg.startswith('highlight_whole_cluster='):
                    self.highlight_whole_cluster=distutils.util.strtobool(arg.replace('highlight_whole_cluster=',''))
                if arg.startswith('compactness='):
                    self.compactness=int(arg.replace('compactness=',''))
                if arg.startswith('maximum_number_iterations='):
                    self.maximum_number_iterations=int(arg.replace('maximum_number_iterations=',''))
                if arg.startswith('minimum_size_superpixel='):
                    self.minimum_size_superpixel=float(arg.replace('minimum_size_superpixel=',''))
                if arg.startswith('verbose='):
                    self.verbose=distutils.util.strtobool(arg.replace('verbose=',''))

        #set default values
        if not hasattr(self,'super_pixel_size'):
            self.super_pixel_size=200
        if not hasattr(self,'cluster_number'):
            self.cluster_number=5
        if not hasattr(self,'k_means_cluster_mode'):
            self.k_means_cluster_mode=1
        if not hasattr(self,'histogram_bins'):
            self.histogram_bins=10
        if not hasattr(self,'colorspace'):
            self.colorspace=1
        if not hasattr(self,'open_gui'):
            self.open_gui=True
        if not hasattr(self,'ratio_sobel_image'):
            self.ratio_sobel_image=0
        if not hasattr(self,'show_super_pixel_image'):
            self.show_super_pixel_image=False
        if not hasattr(self,'show_k_clustered_image'):
            self.show_k_clustered_image=False
        if not hasattr(self,'show_border_image'):
            self.show_border_image=False
        if not hasattr(self,'show_mask'):
            self.show_mask=False
        if not hasattr(self,'show_mean_image'):
            self.show_mean_image=False
        if not hasattr(self,'show_sobel_image'):
            self.show_sobel_image=False
        if not hasattr(self,'highlight_whole_cluster'):
            self.highlight_whole_cluster=False
        if not hasattr(self,'compactness'):
            self.compactness=22
        if not hasattr(self,'maximum_number_iterations'):
            self.maximum_number_iterations=10
        if not hasattr(self,'minimum_size_superpixel'):
            self.minimum_size_superpixel=0.4
        if not hasattr(self,'verbose'):
            self.verbose=True
#endregion

        Application_Window=QWidget.__init__(self)               #eigentliches Graphikfenster
#region Gui
        if self.open_gui:


            # widget layout and elements
            #self.setMinimumWidth(500)       #minimum width
            #self.setMinimumHeight(400)      #minimum height
            self.setWindowTitle("Highlight Objects: Options")         #Window Title
            self.setWindowIcon(QIcon(QIcon(os.path.join(icon_path, "SpinningDiscGear.ico"))))       # ???
            layout_vert = QVBoxLayout(self)                     ##sorge dafuer dass Layouts horizontal uebereinader angordnet werden

            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)


            # self.label_parameter=QLabel('Parameters:',self)
            # layout_hor.addWidget(self.label_parameter)


            #Spinboxes


            # number of clusters Spinbox
            layout_hor.addStretch()
            self.label_clusters=QLabel('Number of Clusters',self)
            layout_hor.addWidget(self.label_clusters,Qt.AlignLeft)
            self.cluster_spin_box=QSpinBox(self)
            self.cluster_spin_box.setRange(0,100)
            self.cluster_spin_box.setValue(self.cluster_number)
            self.cluster_spin_box.setToolTip('<font color="black">Number of Clusters for k-means-algorithm. The Parameters for which are clustered are not changed. Default value: 5.</font>')
            #self.cluster_spin_box.setToolTip('<P><b><i><FONT COLOR='#ff0000' FONT SIZE = 4>')
            layout_hor.addWidget(self.cluster_spin_box)


            # Superpixelsize Spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_mean_pixel_size=QLabel('Super-Pixel-Size')
            layout_hor.addWidget(self.label_mean_pixel_size,Qt.AlignLeft)
            self.mps_spin_box=QSpinBox(self)
            self.mps_spin_box.setRange(0,100000)
            self.mps_spin_box.setValue(self.super_pixel_size)
            self.mps_spin_box.setToolTip('<font color="black">Mean Super Pixel Size in regular Pixels. Default Value 200 but has to be adjusted for every type of picture depending on size of objects to highlight and resolution.</font>')
            layout_hor.addWidget(self.mps_spin_box)


            # Compactness Spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_compactness=QLabel('Compactness')
            layout_hor.addWidget(self.label_compactness,Qt.AlignLeft)
            self.compactness_spin_box=QSpinBox(self)
            self.compactness_spin_box.setRange(0,200)
            self.compactness_spin_box.setValue(self.compactness)
            self.compactness_spin_box.setToolTip('<font color="black">Compactness: Parameter in Algorithm for Superpixelization. Determines how strongly color gradients influence the form of the superpixels compared to their position. Also Look in Doku of Slic Algorithm. Adjustment may be usefull. Default value 22.</font>')
            layout_hor.addWidget(self.compactness_spin_box)


            # Maximum Number of Iterations Spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_iterations=QLabel('Iterations')
            layout_hor.addWidget(self.label_iterations,Qt.AlignLeft)
            self.iterations_spin_box=QSpinBox(self)
            self.iterations_spin_box.setRange(1,200)
            self.iterations_spin_box.setValue(self.maximum_number_iterations)
            self.iterations_spin_box.setToolTip('<font color="black">Maximum-number of Iterations for the k-means-algorithm for the superpixelization. The value influences the computation time strongly, but the higher the value the better the clustering. Default value: 10 </font>')
            layout_hor.addWidget(self.iterations_spin_box)


            # Minimum size superpixel Spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_minimum_size_superpixel=QLabel('Minimum Size Superpixel')
            layout_hor.addWidget(self.label_minimum_size_superpixel,Qt.AlignLeft)
            self.minimum_size_superpixel_spin_box=QDoubleSpinBox(self)
            self.minimum_size_superpixel_spin_box.setRange(0,1)
            self.minimum_size_superpixel_spin_box.setSingleStep(0.01)
            self.minimum_size_superpixel_spin_box.setValue(self.minimum_size_superpixel)
            #self.minimum_size_superpixel_spin_box.setToolTip('<span style=\"background-color:black;\">Minimum size(=area) of a superpixel compared to the mean value of all superpixels. Adjustment might be usefull. Default value:0.4 </span>')
            self.minimum_size_superpixel_spin_box.setToolTip('<font color="black">Minimum size(=area) of a superpixel compared to the mean value of all superpixels. Adjustment might be usefull. Default value:0.4 </font>')
            layout_hor.addWidget(self.minimum_size_superpixel_spin_box)


            # k_means-cluster-mode Spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_k_means_cluster_mode=QLabel('k-means cluster mode')
            layout_hor.addWidget(self.label_k_means_cluster_mode,Qt.AlignLeft)
            self.k_means_cluster_mode_spin_box=QSpinBox(self)
            self.k_means_cluster_mode_spin_box.setRange(1,2)
            self.k_means_cluster_mode_spin_box.setValue(self.k_means_cluster_mode)
            self.k_means_cluster_mode_spin_box.setToolTip('<font color="black">Criterion for which the superpixels are clustered. 1: Clustering for the mean of each superpixel in all three colors. 2. Creation of a histogram of the superpixels for all three colors. Then clustering for the histogram bins. </font>')
            layout_hor.addWidget(self.k_means_cluster_mode_spin_box)


            # histogram bins spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_histogram_bins=QLabel('Histogram Bins')
            layout_hor.addWidget(self.label_histogram_bins,Qt.AlignLeft)
            self.histogram_bins_spin_box=QSpinBox(self)
            self.histogram_bins_spin_box.setRange(1,256)
            self.histogram_bins_spin_box.setValue(self.histogram_bins)
            self.histogram_bins_spin_box.setToolTip('<font color="black">Changing this only has an effect if Cluster-Mode==2. Changes the number of histograms of each superpixel. Changing the colorspace will affect this algorithm. Default Value: 10</font>')
            layout_hor.addWidget(self.histogram_bins_spin_box)


            # colorspace spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_colorspace=QLabel('Colorspace')
            layout_hor.addWidget(self.label_colorspace,Qt.AlignLeft)
            self.colorspace_spin_box=QSpinBox(self)
            self.colorspace_spin_box.setRange(1,3)
            self.colorspace_spin_box.setValue(self.colorspace)
            self.colorspace_spin_box.setToolTip('<font color="black">Colorspace which is used. 1 is lab, 2 is I1I2I3 and 3 just processes the grey-colored-image</font>')
            layout_hor.addWidget(self.colorspace_spin_box)


            # ratio sobel image spinbox
            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_ratio_sobel_image=QLabel('Sobel Cluster Mode')
            layout_hor.addWidget(self.label_ratio_sobel_image,Qt.AlignLeft)
            self.ratio_sobel_image_spin_box=QDoubleSpinBox(self)
            self.ratio_sobel_image_spin_box.setRange(0,1)
            self.ratio_sobel_image_spin_box.setSingleStep(0.01)
            self.ratio_sobel_image_spin_box.setValue(self.ratio_sobel_image)
            self.ratio_sobel_image_spin_box.setToolTip('<font color="black">Determines if an image processed with the Sobel-Operator is used for Clustering. The Sobel operator highlights edges (Strong changes of color) in a picture. If the regions in your picture don t differ that much in color but in the frequency of edges this is recommended. 0: no sobel-image is used. 1 the sobel image and the regular image are used for clustering. 2 Only the sobel image is used for clustering. Default is 0.</font>')
            self.ratio_sobel_image_spin_box.setToolTip('<font color="black">If not zero in the algorithm the Sobel-Operator is run through the image and the resulting image is also used for k-means-clustering. This spinbox determines the amount the normal image and the sobel operator is used. Zero means only the image is used 1 mean only the Sobeled-Image is used. 0.5 mean their mean values are the same. Default value: 0. If you want to use the sobeled image too 0.3 is the recommenend value .</font>')
            layout_hor.addWidget(self.ratio_sobel_image_spin_box)


            #Checkboxes
            layout_vert.addSpacing(20)


            #Checkbox Highlight whole cluster
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_highlight_whole_cluster=QLabel('Highlight whole cluster:')
            layout_hor.addWidget(self.label_highlight_whole_cluster,Qt.AlignLeft)
            self.highlight_whole_cluster_checkbox=QCheckBox(self)
            self.highlight_whole_cluster_checkbox.setChecked(2*self.highlight_whole_cluster)
            self.highlight_whole_cluster_checkbox.setToolTip('<font color="black">Shows the, whole cluster of a clicked superpixel not just the regions, that are connected with it. Default value: False</font>')
            layout_hor.addWidget(self.highlight_whole_cluster_checkbox)


            layout_vert.addSpacing(15)


            #Checkbox Show Superpixelimage
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_super_pixel_image=QLabel('Show Superpixelimage')
            layout_hor.addWidget(self.label_show_super_pixel_image,Qt.AlignLeft)
            self.show_super_pixel_image_checkbox=QCheckBox(self)
            self.show_super_pixel_image_checkbox.setChecked(2*self.show_super_pixel_image)
            self.show_super_pixel_image_checkbox.setToolTip('<font color="black">Show Superpixelimage: An image in which the Superpixels are clearly visible. Usefull to adjust the superpixelsize.Default value: False.</font>')
            layout_hor.addWidget(self.show_super_pixel_image_checkbox)

            #Checkbox Mean image
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_mean_image=QLabel('Show Mean Image')
            layout_hor.addWidget(self.label_show_mean_image,Qt.AlignLeft)
            self.show_mean_image_checkbox=QCheckBox(self)
            self.show_mean_image_checkbox.setChecked(2*self.show_mean_image)
            self.show_mean_image_checkbox.setToolTip('<font color="black">Show Mean Image: An Image where the mean value of each superpixel in all used colors is shown. Usefull to determine if the derivation of the mean actually helps to cluster the superpixel in this colorspace. The first 3/1 image are from the colorspace the last 3/1 images are from the sobel image. Warning: The creation of the mean image is REEAALLYY slow. Default value: False.</font>')
            layout_hor.addWidget(self.show_mean_image_checkbox)


            #Checkbox Sobel image
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_sobel_image=QLabel('Show Sobel Image')
            layout_hor.addWidget(self.label_show_sobel_image,Qt.AlignLeft)
            self.show_sobel_image_checkbox=QCheckBox(self)
            self.show_sobel_image_checkbox.setChecked(2*self.show_sobel_image)
            self.show_sobel_image_checkbox.setToolTip('<font color="black">Show Sobel Image: An image where the sobel image (each pixel replaced by the absolute value of its gradient) is shown. Usefull to determine if the derivation of the sobel image actually helps for clustering. Default value: False.</font>')
            layout_hor.addWidget(self.show_sobel_image_checkbox)

            #Checkbox Show K-Clustered Image
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_k_clustered_image=QLabel('Show k-clustered image')
            layout_hor.addWidget(self.label_show_k_clustered_image,Qt.AlignLeft)
            self.label_show_k_clustered_image
            self.show_k_clustered_image_checkbox=QCheckBox(self)
            self.show_k_clustered_image_checkbox.setChecked(2*self.show_k_clustered_image)
            self.show_k_clustered_image_checkbox.setToolTip('<font color="black">Show k-clustered_image: In this image the superpixels are clustered in different groups depending on their parameters set by the cluster-mode.Default value: False.</font>')
            layout_hor.addWidget(self.show_k_clustered_image_checkbox)


            #Checkbox Show Border Image
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_border_image=QLabel('Show border image')
            layout_hor.addWidget(self.label_show_border_image,Qt.AlignLeft)
            self.show_border_image_checkbox=QCheckBox(self)
            self.show_border_image_checkbox.setChecked(2*self.show_border_image)
            self.show_border_image_checkbox.setToolTip('<font color="black">In this image connected superpixels of the same cluster are put together in one region. A click in one region highlights it.Default value: False.</font>')
            layout_hor.addWidget(self.show_border_image_checkbox)


            #Checkbox Show Mask
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_show_mask=QLabel('Show Mask')
            layout_hor.addWidget(self.label_show_mask,Qt.AlignLeft)
            self.show_mask_checkbox=QCheckBox(self)
            self.show_mask_checkbox.setChecked(2*self.show_mask)
            self.show_mask_checkbox.setToolTip('<font color="black">For Debug-Mode only. Shows the final mask created in the script in matplotlib.Default value: False</font>')
            layout_hor.addWidget(self.show_mask_checkbox)


            layout_vert.addSpacing(15)


            #Checkbox verbose
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_verbose=QLabel('Verbose mode activated')
            layout_hor.addWidget(self.label_verbose,Qt.AlignLeft)
            self.checkbox_verbose=QCheckBox(self)
            self.checkbox_verbose.setChecked(self.verbose)
            self.checkbox_verbose.setToolTip('<font color="black">Print out every step. Default value: True.</font>')
            layout_hor.addWidget(self.checkbox_verbose)


            #Checkbox Saving Changes
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_saving_checkbox=QLabel('Save changes')
            layout_hor.addWidget(self.label_saving_checkbox,Qt.AlignLeft)
            self.checkbox_saving=QCheckBox(self)
            self.checkbox_saving.setChecked(True)
            self.checkbox_saving.setToolTip('<font color="black">Save the changes for the parameters for the next Invocation of this script. Default value: True.</font>')
            layout_hor.addWidget(self.checkbox_saving)

            #Checkbox Open Gui-Next-time
            layout_hor=QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            layout_hor.addStretch()
            self.label_gui_next_time_checkbox=QLabel('Open GUI next time')
            layout_hor.addWidget(self.label_gui_next_time_checkbox,Qt.AlignLeft)
            self.checkbox_gui_next_time=QCheckBox(self)
            self.checkbox_gui_next_time.setChecked(True)
            self.checkbox_gui_next_time.setToolTip('<font color="black">If not checked the Gui will not open in the next invocation of the programm. To open the Gui then you have to change the settings in the config file. Default value: True.</font>')
            layout_hor.addWidget(self.checkbox_gui_next_time)



            layout_hor = QHBoxLayout()
            layout_vert.addLayout(layout_hor)
            self.pbConfirm = QPushButton('Start', self)
            self.pbConfirm.pressed.connect(self.start)
            layout_hor.addWidget(self.pbConfirm)
            layout_hor.addStretch()
            self.pbDiscard = QPushButton('Cancel', self)
            self.pbDiscard.pressed.connect(self.cancel)
            layout_hor.addWidget(self.pbDiscard)
            self.application_canceled=True
            self.close()
        else:
            self.start()
#endregion
    def only_superpixelization(self):
            #global just_superpixelization
            self.just_superpixelization=True
            self.start()

    def cancel(self):
            self.application_canceled=True
            self.close()

            #%Fenster schliessen

    def start(self):
        #region read out parameter set in gui
        if self.open_gui:
            self.super_pixel_size=self.mps_spin_box.value()
            self.cluster_number=self.cluster_spin_box.value()
            self.compactness=self.compactness_spin_box.value()
            self.maximum_number_iterations=self.iterations_spin_box.value()
            self.minimum_size_superpixel=self.minimum_size_superpixel_spin_box.value()
            self.k_means_cluster_mode=self.k_means_cluster_mode_spin_box.value()
            self.histogram_bins=self.histogram_bins_spin_box.value()
            self.colorspace=self.colorspace_spin_box.value()
            self.ratio_sobel_image=self.ratio_sobel_image_spin_box.value()
            self.verbose=self.checkbox_verbose.checkState()
            self.show_super_pixel_image=self.show_super_pixel_image_checkbox.checkState()
            self.show_mean_image=self.show_mean_image_checkbox.checkState()
            self.show_sobel_image=self.show_sobel_image_checkbox.checkState()
            self.show_k_clustered_image=self.show_k_clustered_image_checkbox.checkState()
            self.show_border_image=self.show_border_image_checkbox.checkState()
            self.show_mask=self.show_mask_checkbox.checkState()
            self.highlight_whole_cluster=self.highlight_whole_cluster_checkbox.checkState()

        self.application_canceled=False
        if self.show_super_pixel_image | self.show_k_clustered_image | self.show_border_image\
                |self.show_mask | self.show_sobel_image | self.show_mean_image:             ##insert more condtions later for example return true also if clustered image is required
            self.return_just_mask=False
        else:
            self.return_just_mask=True

        # write settings in config file
        if (hasattr(self,'checkbox_saving') and self.checkbox_saving.checkState()):
            self.open_gui=bool(self.checkbox_gui_next_time.checkState())
            if Param_object.verbose:
                print('Saving changes')
            self.file.seek(0)
            self.file.truncate(0)
            self.file.write('This is an auto-generated config file with the values from the GUI.')
            self.file.write('\ncluster_number=%i'%(self.cluster_number))
            self.file.write('\nsuper_pixel_size=%i'%(self.super_pixel_size))
            self.file.write('\ncompactness=%i'%(self.compactness))
            self.file.write('\nmaximum_number_iterations=%i'%(self.maximum_number_iterations))
            self.file.write('\nminimum_size_superpixel=%f'%(self.minimum_size_superpixel))
            self.file.write('\nk_means_cluster_mode=%i'%(self.k_means_cluster_mode))
            self.file.write('\nhistogram_bins=%i'%(self.histogram_bins))
            self.file.write('\ncolorspace=%i'%(self.colorspace))
            self.file.write('\nratio_sobel_image=%f'%(self.ratio_sobel_image))
            self.file.write('\nverbose=%s'%str((bool(self.verbose))))
            self.file.write('\nopen_gui=%s'%str((bool(self.open_gui))))
            self.file.write('\nshow_super_pixel_image=%s'%(bool(self.show_super_pixel_image)))
            self.file.write('\nshow_mean_image=%s'%str((bool(self.show_mean_image))))
            self.file.write('\nshow_sobel_image=%s'%str((bool(self.show_sobel_image))))
            self.file.write('\nshow_mean_image=%s'%str((bool(self.show_mean_image))))
            self.file.write('\nshow_sobel_image=%s'%str((bool(self.show_sobel_image))))
            self.file.write('\nshow_k_clustered_image=%s'%str((bool(self.show_k_clustered_image))))
            self.file.write('\nshow_border_image=%s'%str((bool(self.show_border_image))))
            self.file.write('\nshow_mask=%s'%str((bool(self.show_mask))))
            self.file.write('\nhighlight_whole_cluster=%s'%str((bool(self.highlight_whole_cluster))))


        self.file.close()
        #endregion

        #if hasobject('Param_object') & Param_object.verbose:
        if self.open_gui:
            print('Input window shut down normally')
        print('Parameters Extracted')
            # print('Number of clusters for k-means-clustering = %i'%(self.cluster_number))
            # print('Super-Pixel-Size = %i'%(self.super_pixel_size))
            # print('Open gui next time=',self.open_gui)
        print('Segmentation Starting')

        self.close()


if __name__ == '__main__':
    print("Starting HighlightObjects", sys.argv)
    # connect to ClickPoints database and the running program instance
    # database filename and port for communication are supplied as command line argument when started from ClickPoints
    import clickpoints
    start_frame, database, port = clickpoints.GetCommandLineArgs()
    db = clickpoints.DataFile(database)
    com = clickpoints.Commands(port, catch_terminate_signal=True)

    # get the image
    image = db.GetImages(start_frame=start_frame)[0]

    points = db.GetMarker(image=image.id)
    #print("query", points)
    print("hightlight", points.count(), image.id)

    try:
        x, y = points[0].x, points[0].y
        coords=[]
        for i,point in enumerate(points):
            coords.append([points[i].x,points[i].y])

    except IndexError:
        print("ERROR: no markers present")
        sys.exit(-1)

    mask = np.zeros(image.data.shape, "uint8")
    print('clicked coordinates are=',coords)
    #endregion


    #region get Parameters from config_file and Gui for image Segmentation
    #region Start Gui
    app = QApplication(sys.argv)
    app.setStyle('cleanlooks')

    Param_object = Param_Delivery()
    if Param_object.open_gui:
        Param_object.show()
        app.exec_()


    if Param_object.verbose:
        print('Got Parameter')


    #endregion
    #endregion
    if(Param_object.application_canceled):
        print('Application canceled')
    else:
        #region create mask
        if Param_object.return_just_mask:
            image_segmented=image_segmenter(image.data, coords, mean_pixel_size=Param_object.super_pixel_size, compactness=Param_object.compactness,
                                            min_size=Param_object.minimum_size_superpixel, iterations=Param_object.maximum_number_iterations, verbose=Param_object.verbose,
                                            k_mean_cluster_number=Param_object.cluster_number, highlight_whole_cluster=Param_object.highlight_whole_cluster,
                                            k_means_cluster_mode=Param_object.k_means_cluster_mode, histogram_bins=Param_object.histogram_bins, colorspace=Param_object.colorspace,
                                            ratio_sobel_image=Param_object.ratio_sobel_image)
            mask=image_segmented.mask

        else:
            image_segmented=image_segmenter(image.data, coords, mean_pixel_size=Param_object.super_pixel_size, compactness=Param_object.compactness,
                                            min_size=Param_object.minimum_size_superpixel, iterations=Param_object.maximum_number_iterations, verbose=Param_object.verbose,
                                            k_mean_cluster_number=Param_object.cluster_number, create_all_images=True, highlight_whole_cluster=Param_object.highlight_whole_cluster,
                                            k_means_cluster_mode=Param_object.k_means_cluster_mode, histogram_bins=Param_object.histogram_bins, colorspace=Param_object.colorspace,
                                            ratio_sobel_image=Param_object.ratio_sobel_image)
            mask=image_segmented.mask

            used_figures=int(1)
            if Param_object.show_super_pixel_image:
                #super_pixel_image=image_segmented.get_super_pixel_marked_image()
                plt.figure(used_figures)
                plt.imshow(image_segmented.super_pixel_image)
                plt.title('Superpixel segmented image')
                used_figures+=1
            if Param_object.show_mean_image:
                image_segmented.get_mean_regions()
                for color in range(image_segmented.mean_regions_col.shape[2]):
                    plt.figure(used_figures)
                    plt.imshow(image_segmented.mean_regions_col[:,:,color])
                    plt.title('Mean Image color=%i'%(color))
                    used_figures+=1
            if Param_object.show_sobel_image:
                if hasattr(image_segmented,'sobel_im'):
                    for color in range(image_segmented.sobel_im.shape[2]):
                        plt.figure(used_figures)
                        plt.imshow(image_segmented.sobel_im[:,:,color])
                        plt.title('Sobel Image color=%i'%(color))
                        used_figures+=1
                else:
                    print('No Sobel Image created so no Sobel Image shown')
                used_figures+=1
            if Param_object.show_k_clustered_image:
                plt.figure(used_figures)
                plt.imshow(image_segmented.k_mean_clustered_regions)
                plt.title('k-clustered image')
                used_figures+=1
            if Param_object.show_border_image:
                plt.figure(used_figures)
                plt.imshow(image_segmented.connected_regions_marked_boarders_image)
                plt.title('Border image')
                used_figures+=1
            if Param_object.show_mask:
                plt.figure(used_figures)
                plt.imshow(image_segmented.mask)
                plt.title('Final Mask')
                used_figures+=1
            plt.show()


        if Param_object.verbose:
            print('Mask created')
        db.SetMask(mask, image.id)
        db.db.close()
        com.ReloadMask()

        #endregion

    print("Highlight_Objects Finished")