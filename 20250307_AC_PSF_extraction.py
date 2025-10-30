# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 10:19:22 2025

@author: afc1n18
"""

import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QFileDialog
from scipy.optimize import curve_fit
from scipy.ndimage import gaussian_filter, measurements, center_of_mass
from scipy.stats import linregress
from skimage.transform import resize
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm
fontprops = fm.FontProperties(size=15)
from PIL import Image
import os
import cv2
import pandas as pd
import csv
import tifffile

class PSF_extraction():
    def __init__(self,
            min_threshold=0.4, #Minimum pixel brightness to be considered when findng beads
            max_threshold=1.0, #Maximum pixel brightness to be considered when findng beads
            num_points=60, #Number of pixels to be analysed
            min_distance=25, #Minimum separation of bead coordinates in pixels
            min_size=10, #Rough size of the bead in pixels
            start_z=0, #Start plane of bead stack
            end_z=5000, #End plane of bead stack
            blur_sigma=0, #Sigma value of gaussian blurring
            step=268, #Conversion value of pixels relative to the units desired for presentation
            step_z=50, #Conversion value of z step to the units desired for presentation
            convert_scales=True, #If true will convert values to the desired units
            units='nm', #Units desired for presentation purposes
            many_clusters=False, #If True will attempt to filter out bead clusters
            mean_min_threshold=5, #Only if many_clusters is True, lower threshold for the first half of the histogram used to filter out bead clusters  
            mean_max_threshold=1.5, #Only if many_clusters is True, upper threshold for the second half of the histogram used to filter out bead clusters  
            ):
            
        super().__init__()
        
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.num_points = num_points
        self.min_distance = min_distance
        self.min_size = min_size
        self.vol_size = int(min_size*0.75)
        self.edge_distance = min_size
        self.start_z = start_z
        self.end_z = end_z
        self.blur_sigma = blur_sigma
        self.convert_scales = convert_scales
        if self.convert_scales == True:
            self.units = units
            self.step = step
            self.step_z = step_z
        if self.convert_scales == False:
            self.units = 'Pixels'
            self.step = 1
            self.step_z = 1
        self.many_clusters = many_clusters
        self.mean_min_threshold = mean_min_threshold
        self.mean_max_threshold = mean_max_threshold
        
        self.volumes = []
        
        self.inputs={
            'min_threshold': self.min_threshold,
            'max_threshold': self.max_threshold,
            'num_points': self.num_points,
            'min_distance': self.min_distance,
            'min_size:': self.min_size,
            'Start z:': self.start_z,
            'End z:': self.end_z,
            'edge_distance:': self.edge_distance,
            'mean_min_threshold:': self.mean_min_threshold,
            'mean_max_threshold:': self.mean_max_threshold,
            'blur_sigma:': self.blur_sigma,
            'step:': self.step,
            'convert_scales:': self.convert_scales,
            'units:': self.units,
            'many_clusters:': self.many_clusters
            }


        
    def extract_PSF(self):
        self.folder_path = self.open_folder_dialog()
        self.fwhm_results = self.process_images()
        self.produce_csv()
        self.analyze_fwhm()
        self.produce_volume()

        
        
    def nonzero_mean(self, a):
        num=len(np.nonzero(a)[0])
        val=np.sum(a)
        mean=val/num
        return mean
    
    # 1. Dialog to Select Folder of .tif Files
    def open_folder_dialog(self):
        app = QApplication(sys.argv)
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.Directory)
        if folder_dialog.exec_():
            folder_path = folder_dialog.selectedFiles()[0]
            return folder_path
        sys.exit()
    
    
    # 2. Function to find brightest points in the 3D image (with Gaussian blur and distance exclusion)
    def find_brightest_points(self, image):
        # Normalize image
        image_normalized = image / np.max(image)
    
        # Find points above threshold
        bright_points = np.where((image_normalized > self.min_threshold) & (image_normalized < self.max_threshold))
    
        intensities = image_normalized[bright_points]
    
        # Get the brightest points sorted by intensity
        brightest_indices = np.argsort(intensities)[::-1]  # Sort in descending order of intensity
    
        print(len(brightest_indices))
    
        selected_points = []
    
        for idx in brightest_indices:
            point = (bright_points[0][idx], bright_points[1][idx], bright_points[2][idx])  # (z, y, x) point
        
            # Check if the point is at least 'min_distance' away from all previously selected points
            too_close = any(np.sqrt((point[0] - p[0])**2 + (point[1] - p[1])**2 + (point[2] - p[2])**2) < self.min_distance for p in selected_points)
            if not too_close:
                selected_points.append(point)
        
            # Stop when we have enough points
            if len(selected_points) >= self.num_points:
                break
            
        print(len(selected_points))
        # Filter out points that are too close to the edges
        filtered_points = []
        for z, y, x in selected_points:
            if (self.edge_distance <= x < self.width - self.edge_distance) and (self.edge_distance <= y < self.height - self.edge_distance) and (self.edge_distance <= z < self.depth - self.edge_distance):   
                filtered_points.append((z, y, x))
                
        print(len(filtered_points))
      
        #Filter out points that correspond to clumps
        if self.depth > 1 and self.many_clusters == True:
            bead_points=[] 
        
            fil=np.zeros((2*self.min_size, 2*self.min_size, 2*self.min_size))
        
            for z_idx, y_idx, x_idx in filtered_points:
                fil[:]=image[z_idx-self.min_size:z_idx+self.min_size, y_idx-self.min_size:y_idx+self.min_size, x_idx-self.min_size:x_idx+self.min_size] 
                hist=np.histogram(fil, bins=255)
                #if self.nonzero_mean(hist[0][0:25]) > self.mean_min_threshold and self.nonzero_mean(hist[0][50:]) < self.mean_max_threshold:
                if np.amax(hist[0]) > 350:
                    plt.figure()
                    plt.plot(range(len(hist[0])),hist[0])
                    plt.show()
                    plt.figure()
                    plt.imshow(fil[self.min_size,:,:])
                    plt.show()
                    plt.figure()
                    plt.imshow(fil[:,self.min_size,:])
                    plt.show()
                    plt.figure()
                    plt.imshow(fil[:,:,self.min_size])
                    plt.show()
                    bead_points.append((z_idx, y_idx, x_idx))

            print(len(bead_points))
            #print(bead_points)
            return bead_points
        else:
            print(filtered_points)
            return filtered_points
    
    # 3. 1D Gaussian Function
    def gaussian(self, x, amp, mu, sigma):
        return amp * np.exp(-(x - mu)**2 / (2 * sigma**2))
    
    # Function to fit Gaussian and get FWHM
    def fit_gaussian_1d(self, data, axis_values):
        mean = np.sum(axis_values * data) / np.sum(data)
        sigma = np.sqrt(np.sum(data * (axis_values - mean) ** 2) / np.sum(data))

        popt, _ = curve_fit(self.gaussian, axis_values, data, p0=[np.max(data), mean, sigma])
        amplitude, mu, sigma_fitted = popt
        fwhm = 2 * np.sqrt(2 * np.log(2)) * np.abs(sigma_fitted)  # FWHM formula
        return fwhm, amplitude, mu, sigma_fitted
    
    def process_images(self):
        # Load all .tif files in the selected folder and stack them
        images = []
        self.file_list=os.listdir(self.folder_path)
        self.depth = len(self.file_list)
        for filename in sorted(self.file_list[self.start_z:self.end_z]):
            if filename.endswith('.tif'):
                img_path = os.path.join(self.folder_path, filename)
                image = Image.open(img_path)#.convert('L')  # Convert image to grayscale
                image = np.array(image)
                images.append(image)
        
        self.height = np.shape(image)[0]
        
        self.width= np.shape(image)[1]

        # Convert the list of images to a 3D NumPy array (stack)
        image_stack = np.array(images)
        
        # Print folder path and number of images found
        print(f"Selected Folder: {self.folder_path}")
        print(f"Number of .tif images found: {len(images)}")
        
        self.depth = int(self.depth * self.step_z / self.step)
        
        # Interpolate along the z-axis only. The zoom factors for (z, y, x) are (zoom_factor_z, 1, 1).
        image_stack = resize(image_stack, (self.depth, self.height, self.width),
                        order=1, anti_aliasing=True)
        
        print('Image resized')

        # Apply Gaussian blur to the entire image stack to reduce noise
        image_stack_blurred = gaussian_filter(image_stack, sigma=self.blur_sigma)
        
        print('Image blurring complete')

        # Find the brightest points in the blurred 3D image
        brightest_points = self.find_brightest_points(image_stack_blurred)
        
        print(f"Brightest Points (z, y, x): {brightest_points}")

        # Fit Gaussian for each filtered brightest point and get FWHM
        self.fwhm_results = []
        z_axis_main = np.arange(self.depth)  # Assuming Z-axis is the stack index
        y_axis_main = np.arange(self.height)
        x_axis_main = np.arange(self.width)
        
        self.fwhm_results_pd = []
        for z, y, x in brightest_points:
            # Extract the 3D data around the point
            if self.depth > 1:
                self.z_axis=z_axis_main[z-self.min_size:z+self.min_size]
                self.z_profile=image_stack_blurred[z-self.min_size:z+self.min_size, y, x]
                self.z_profile=self.z_profile-np.amin(self.z_profile)
            else:
                self.z_axis, self.z_profile = (0,0)
            self.y_axis=y_axis_main[y-self.min_size:y+self.min_size]
            self.y_profile=image_stack_blurred[z, y-self.min_size:y+self.min_size, x]
            self.y_profile=self.y_profile-np.amin(self.y_profile)
            self.x_axis=x_axis_main[x-self.min_size:x+self.min_size]
            self.x_profile=image_stack_blurred[z, y, x-self.min_size:x+self.min_size]
            self.x_profile=self.x_profile-np.amin(self.x_profile)
            try:
                # Fit Gaussian to the 3D data
                self.fwhm_x, self.amp_x, self.mu_x, self.sigma_x = self.fit_gaussian_1d(self.x_profile, self.x_axis)
                  
                self.x_gaussian = self.gaussian(self.x_axis, self.amp_x, self.mu_x, self.sigma_x)
                        
                _, _, self.x_r_value, _, _ = linregress(self.x_profile, self.x_gaussian)
                
                self.r2_x = self.x_r_value**2
                
                self.fwhm_y, self.amp_y, self.mu_y, self.sigma_y = self.fit_gaussian_1d(self.y_profile, self.y_axis)
                
                self.y_gaussian = self.gaussian(self.y_axis, self.amp_y, self.mu_y, self.sigma_y)
                
                _, _, self.y_r_value, _, _ = linregress(self.y_profile, self.y_gaussian)
                
                self.r2_y = self.y_r_value**2
                
                if self.depth > 1:
                
                    self.fwhm_z, self.amp_z, self.mu_z, self.sigma_z = self.fit_gaussian_1d(self.z_profile, self.z_axis)
                
                    self.z_gaussian = self.gaussian(self.z_axis, self.amp_z, self.mu_z, self.sigma_z)
                
                    _, _, self.z_r_value, _, _ = linregress(self.z_profile, self.z_gaussian)
                
                    self.r2_z = self.z_r_value**2
                

                else:

                    self.fwhm_z, self.amp_z, self.mu_z, self.sigma_z, self.z_gaussian, self.z_r_value, self.r2_z = (0, 0, 0, 0, 0, 0, 0)
                
                if self.convert_scales == False:
                    self.fwhm_values = (self.fwhm_x, self.fwhm_y, self.fwhm_z)
                else:
                    self.fwhm_values = (self.fwhm_x*self.step, self.fwhm_y*self.step, self.fwhm_z*self.step)
                
                self.params = (self.amp_x, self.amp_y, self.amp_z, self.mu_x, self.mu_y, self.mu_z, self.sigma_x, self.sigma_y, self.sigma_z)
                
                if self.r2_x > 0.8 and self.r2_y > 0.8:
                
                    # print(self.fwhm_z,self.fwhm_y,self.fwhm_x) 
                    self.fwhm_results.append({
                        'point': (x, y, z),
                        'fwhm': self.fwhm_values,
                        'params': self.params,
                        'x_gaussian': self.x_gaussian,
                        'y_gaussian': self.y_gaussian,
                        'z_gaussian': self.z_gaussian
                        })

                    

                    self.fwhm_results_pd.append({
                        'point': (x, y, z),
                        'fwhm_x': self.fwhm_x,
                        'fwhm_y': self.fwhm_y,
                        'fwhm_z': self.fwhm_z,
                        'fwhm_x ('+self.units+')': self.fwhm_x*self.step,
                        'fwhm_y ('+self.units+')': self.fwhm_y*self.step,
                        'fwhm_z ('+self.units+')': self.fwhm_z*self.step,
                        'r2_x': self.r2_x,
                        'r2_y': self.r2_y,
                        'r2_z': self.r2_z
                        })

                    self.volumes.append(image_stack_blurred[z-self.min_size:z+self.min_size, y-self.min_size:y+self.min_size, x-self.min_size:x+self.min_size])
                    # Plotting: 50x50 pixel region and Gaussian fits for X, Y, Z
                    self.plot_gaussian_fits(image_stack_blurred, (x, y, z))
                else:
                    print('r2_x or r2_y too low')
            except:
                print('Error')
    
        return self.fwhm_results
    
    
    # Function to plot region and Gaussian fits for X, Y, and Z axes
    def plot_gaussian_fits(self, image_stack, point):

        x, y, z = point
        
        # Extract 50x50 region around the point
        region = image_stack[z, y-self.min_size:y+self.min_size, x-self.min_size:x+self.min_size]

        # Create figure
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))

        # Plot 50x50 region
        axs[0, 0].imshow(region, cmap='gray')
        scalebar_size=self.min_size
        scalebar = AnchoredSizeBar(axs[0, 0].transData,
                        scalebar_size, str(scalebar_size*self.step) + ' '+self.units, 'lower center', 
                        pad=0.01,
                        color='white',
                        frameon=False,
                        size_vertical=0.1,
                        fontproperties=fontprops)
        axs[0, 0].add_artist(scalebar)
        axs[0, 0].set_title('('+str(x)+','+str(y)+')')
        axs[0, 0].scatter(self.min_size, self.min_size, color='red')  # Mark the bright point in the center


        # Plot X-axis intensity profile and Gaussian fit
        x_range=np.linspace(min(self.x_axis),max(self.x_axis),5)
        x_ticks=np.linspace(-len(self.x_axis)//2,len(self.x_axis)//2,5)
        axs[0, 1].plot(self.x_axis, self.x_profile, label='X Profile')
        axs[0, 1].plot(self.x_axis, self.x_gaussian, label='Gaussian Fit', linestyle='--')
        axs[0, 1].set_xticks(x_range)
        axs[0, 1].set_xticklabels(x_ticks*self.step)
        axs[0, 1].set_xlabel('X Distance ('+self.units+')')
        axs[0, 1].set_title('X-axis Profile')
        axs[0, 1].legend()


        # Plot Y-axis intensity profile and Gaussian fit
        y_range=np.linspace(min(self.y_axis),max(self.y_axis),5)
        y_ticks=np.linspace(-len(self.y_axis)//2,len(self.y_axis)//2,5)
        y_profile = image_stack[z, y-self.min_size:y+self.min_size, x]
        y_profile=y_profile-np.amin(y_profile)
        axs[1, 0].plot(self.y_axis, self.y_profile, label='Y Profile')
        axs[1, 0].plot(self.y_axis, self.y_gaussian, label='Gaussian Fit', linestyle='--')
        axs[1, 0].set_xticks(y_range)
        axs[1, 0].set_xticklabels(y_ticks*self.step)
        axs[1, 0].set_xlabel('Y Distance ('+self.units+')')
        axs[1, 0].set_title('Y-axis Profile')
        axs[1, 0].legend()

        if self.depth > 1:
            z_range=np.linspace(min(self.z_axis),max(self.z_axis),5)
            z_ticks=np.linspace(-len(self.z_axis)//2,len(self.z_axis)//2,5)
            axs[1, 1].plot(self.z_axis, self.z_profile, label='Z Profile')
            axs[1, 1].plot(self.z_axis, self.z_gaussian, label='Gaussian Fit', linestyle='--')
            axs[1, 1].set_xticks(z_range)
            axs[1, 1].set_xticklabels(z_ticks*self.step)
            axs[1, 1].set_xlabel('Z Distance ('+self.units+')')
            axs[1, 1].set_title('Z-axis Profile')
            axs[1, 1].legend()

        plt.tight_layout()
        plt.show()
        
    def produce_csv(self):
        #Export fitting results to csv via pandas dataframe
        self.fwhm_results_pd = pd.DataFrame(self.fwhm_results_pd)
        self.fwhm_results_pd.to_csv(self.folder_path+'.csv', index=False)
        
        with open(self.folder_path+'.csv', "a") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([])
            for key, value in self.inputs.items():
                writer.writerow([key, value])
        
        # self.inputs_pd = pd.DataFrame(self.inputs)
        # self.inputs_pd.to_csv(self.folder_path+'_inputs.csv', index=False)
        
        
    def produce_volume(self):
        
        volume = np.zeros((2*self.vol_size, 2*self.vol_size, 2*self.vol_size))
        
        offset = (self.min_size-self.vol_size)
        
        for vol_idx in range(len(self.volumes)):
            vol = self.volumes[vol_idx]
            vol_norm = vol - np.amin(vol)
            vol_norm = vol_norm/np.amax(vol_norm)
            com = center_of_mass(vol_norm[self.min_size,...])
            print(com)
            com_y = int(np.round(com[0]))
            com_x = int(np.round(com[1]))
            new_vol = vol[offset:-offset,com_y-self.vol_size:com_y+self.vol_size,com_x-self.vol_size:com_x+self.vol_size,]
            volume += new_vol/len(self.volumes)
            
            
        
        axis=np.arange(2*self.vol_size)    
        
        if self.depth > 1:
            z_profile=volume[:, self.vol_size, self.vol_size]
            z_profile=z_profile-np.amin(z_profile)

        y_profile=volume[self.vol_size, :, self.vol_size]
        y_profile=y_profile-np.amin(self.y_profile)
        x_profile=volume[self.vol_size, self.vol_size,:]
        x_profile=x_profile-np.amin(self.x_profile)
        
        fwhm_x, amp_x, mu_x, sigma_x = self.fit_gaussian_1d(x_profile, axis)
                  
        x_gaussian = self.gaussian(axis, amp_x, mu_x, sigma_x)
                
        fwhm_y, amp_y, mu_y, sigma_y = self.fit_gaussian_1d(y_profile, axis)
                
        y_gaussian = self.gaussian(axis, amp_y, mu_y, sigma_y)
                
        if self.depth > 1:
                
            fwhm_z, amp_z, mu_z, sigma_z = self.fit_gaussian_1d(z_profile, axis)
                
            z_gaussian = self.gaussian(axis, amp_z, mu_z, sigma_z)
                
        
        # Create figure
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))

        # Plot 50x50 region
        axs[0, 0].imshow(volume[self.vol_size,:,:], cmap='gray')
        scalebar_size=self.vol_size
        scalebar = AnchoredSizeBar(axs[0, 0].transData,
                        scalebar_size, str(scalebar_size*self.step) + ' '+self.units, 'lower center', 
                        pad=0.01,
                        color='white',
                        frameon=False,
                        size_vertical=0.1,
                        fontproperties=fontprops)
        axs[0, 0].add_artist(scalebar)
        axs[0, 0].set_title('XY Profile')
        axs[0, 0].scatter(self.vol_size, self.vol_size, color='red')  # Mark the bright point in the center


        # Plot X-axis intensity profile and Gaussian fit
        x_range=np.linspace(0,2*self.vol_size,5)
        x_ticks=np.linspace(-self.vol_size,self.vol_size,5)
        axs[0, 1].plot(axis, x_profile, label='X Profile')
        axs[0, 1].plot(axis, x_gaussian, label='Gaussian Fit', linestyle='--')
        axs[0, 1].set_xticks(x_range)
        axs[0, 1].set_xticklabels(x_ticks*self.step)
        axs[0, 1].set_xlabel('X Distance ('+self.units+')')
        axs[0, 1].set_title('X-axis Profile')
        axs[0, 1].legend()


        # Plot Y-axis intensity profile and Gaussian fit
        y_range=np.linspace(0,2*self.vol_size,5)
        y_ticks=np.linspace(-self.vol_size,self.vol_size,5)
        axs[1, 0].plot(axis, y_profile, label='Y Profile')
        axs[1, 0].plot(axis, y_gaussian, label='Gaussian Fit', linestyle='--')
        axs[1, 0].set_xticks(y_range)
        axs[1, 0].set_xticklabels(y_ticks*self.step)
        axs[1, 0].set_xlabel('Y Distance ('+self.units+')')
        axs[1, 0].set_title('Y-axis Profile')
        axs[1, 0].legend()

        if self.depth > 1:
            z_range=np.linspace(0,2*self.vol_size,5)
            z_ticks=np.linspace(-self.vol_size,self.vol_size,5)
            axs[1, 1].plot(axis, z_profile, label='Z Profile')
            axs[1, 1].plot(axis, z_gaussian, label='Gaussian Fit', linestyle='--')
            axs[1, 1].set_xticks(z_range)
            axs[1, 1].set_xticklabels(z_ticks*self.step)
            axs[1, 1].set_xlabel('Z Distance ('+self.units+')')
            axs[1, 1].set_title('Z-axis Profile')
            axs[1, 1].legend()

        plt.tight_layout()
        plt.show()   
        
        print(f'FWHM for X-axis: {fwhm_x*self.step:.2f} '+self.units)
        print(f'FWHM for Y-axis: {fwhm_y*self.step:.2f} '+self.units)
        print(f'FWHM for Z-axis: {fwhm_z*self.step:.2f} '+self.units)
        
        tifffile.imwrite(self.folder_path+'.tif', (65535*volume/255).astype(np.int16))
        
        
    # 5. Function to compute FWHM, print averages, and plot histograms
    def analyze_fwhm(self):
        x_fwhms = []
        y_fwhms = []
        z_fwhms = []

        
        xs = []
        ys = []
        zs = []
        

        # Collect FWHM values for x, y, and z
        for result in self.fwhm_results:
            x, y, z = result['point']
            xs.append(x)
            ys.append(y)
            zs.append(z)
            
            fwhm_x, fwhm_y, fwhm_z = result['fwhm']
            x_fwhms.append(fwhm_x)
            y_fwhms.append(fwhm_y)
            z_fwhms.append(fwhm_z)
            print(self.fwhm_results.index(result))
            print('x_coordinate = '+str(x))
            print('x fwhm = '+str(fwhm_x))
            print('y_coordinate = '+str(y))
            print('y fwhm = '+str(fwhm_y))
            print('z_coordinate = '+str(z))
            print('z fwhm = '+str(fwhm_z))
        
            
        
        # Calculate averages
        avg_fwhm_x = np.mean(x_fwhms)
        avg_fwhm_y = np.mean(y_fwhms)
        avg_fwhm_z = np.mean(z_fwhms)
            
        
        print(f'Average FWHM for X-axis: {avg_fwhm_x:.2f} '+self.units)
        print(f'Average FWHM for Y-axis: {avg_fwhm_y:.2f} '+self.units)
        print(f'Average FWHM for Z-axis: {avg_fwhm_z:.2f} '+self.units)
        
        
        
        # Plot histograms for FWHM values (X, Y, Z)
        
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.hist(xs, bins=15, color='blue', alpha=0.7, label='X FWHM')
        plt.title('Histogram of X positions')
        plt.xlabel('Position ('+self.units+')')
        plt.ylabel('Frequency')
        plt.legend()

        plt.subplot(1, 3, 2)
        plt.hist(ys, bins=15, color='green', alpha=0.7, label='Y FWHM')
        plt.title('Histogram of Y  positions')
        plt.xlabel('Position ('+self.units+')')
        plt.ylabel('Frequency')
        plt.legend()
        
        if self.depth > 1:
        
            plt.subplot(1, 3, 3)
            plt.hist(zs, bins=15, color='red', alpha=0.7, label='Z FWHM')
            plt.title('Histogram of Z positions')
            plt.xlabel('Position ('+self.units+')')
            plt.ylabel('Frequency')
            plt.legend()

        plt.tight_layout()
        plt.show()
        
        plt.figure(figsize=(15, 5))
        
        # plt.subplot(1, 3, 1)
        # plt.plot(np.arange(-15,15,1), avg_x_gaussian, color='blue', label='X')
        # plt.title('Average X Gaussian')
        # plt.xlabel('Width')
        # plt.ylabel('Height')
        # plt.legend()

        # plt.subplot(1, 3, 2)
        # plt.plot(np.arange(-15,15,1), avg_y_gaussian, color='green', label='Y')
        # plt.title('Average Y Gaussian')
        # plt.xlabel('Width')
        # plt.ylabel('Height')
        # plt.legend()
        
        # plt.subplot(1, 3, 3)
        # plt.plot(np.arange(-10,10,1), avg_z_gaussian, color='red', label='Z')
        # plt.title('Average Z Gaussian')
        # plt.xlabel('Width')
        # plt.ylabel('Height')
        # plt.legend()
        
        plt.subplot(1, 3, 1)
        plt.hist(x_fwhms, bins=15, color='blue', alpha=0.7, label='X FWHM')
        plt.title('Histogram of X FWHM')
        plt.xlabel('FWHM (X) ('+self.units+')')
        plt.ylabel('Frequency')
        plt.legend()

        plt.subplot(1, 3, 2)
        plt.hist(y_fwhms, bins=15, color='green', alpha=0.7, label='Y FWHM')
        plt.title('Histogram of Y FWHM')
        plt.xlabel('FWHM (Y) ('+self.units+')')
        plt.ylabel('Frequency')
        plt.legend()
        
        if self.depth > 1:
            plt.subplot(1, 3, 3)
            plt.hist(z_fwhms, bins=15, color='red', alpha=0.7, label='Z FWHM')
            plt.title('Histogram of Z FWHM')
            plt.xlabel('FWHM (Z) ('+self.units+')')
            plt.ylabel('Frequency')
            plt.legend()

        plt.tight_layout()
        plt.show()

#%%

psf_extractor = PSF_extraction()

psf_extractor.extract_PSF()
    
    
    
    