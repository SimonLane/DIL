# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 17:42:04 2025

@author: sil1r12
"""

import os, sys, glob
import numpy as np
import pandas as pd
import imageio.v2 as imageio
from scipy.ndimage import label, center_of_mass, gaussian_filter, maximum_filter, generate_binary_structure
from skimage.transform import resize
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

def fill_water_bridges_3D(arr):
    """ Convert isolated '0' pixels into '1' if they touch land on at least two sides in 3D """
    filled_arr = arr.copy()
    depth, rows, cols = arr.shape
    
    for d in range(1, depth - 1):
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if arr[d, r, c] == 0:  # Check water pixels
                    # Get all 26 neighboring values in 3D
                    neighbors = [
                        arr[d-1, r, c], arr[d+1, r, c],  # Z-axis
                        arr[d, r-1, c], arr[d, r+1, c],  # Y-axis
                        arr[d, r, c-1], arr[d, r, c+1],  # X-axis
                        arr[d-1, r-1, c], arr[d-1, r+1, c], arr[d-1, r, c-1], arr[d-1, r, c+1],  # Diagonal in Z-1
                        arr[d+1, r-1, c], arr[d+1, r+1, c], arr[d+1, r, c-1], arr[d+1, r, c+1],  # Diagonal in Z+1
                        arr[d, r-1, c-1], arr[d, r-1, c+1], arr[d, r+1, c-1], arr[d, r+1, c+1],  # XY-plane diagonals
                        arr[d-1, r-1, c-1], arr[d-1, r-1, c+1], arr[d-1, r+1, c-1], arr[d-1, r+1, c+1],  # 3D diagonals in Z-1
                        arr[d+1, r-1, c-1], arr[d+1, r-1, c+1], arr[d+1, r+1, c-1], arr[d+1, r+1, c+1]   # 3D diagonals in Z+1
                    ]
                    if neighbors.count(1) >= 2:  # If at least two neighbors are land
                        filled_arr[d, r, c] = 1  # Convert water to land
    
    return filled_arr

def gaussian(x, amplitude, mean, sigma, offset):
    return offset + amplitude * np.exp(-((x - mean)**2) / (2 * sigma**2))

def fit_gaussian_to_profile(x, profile):
    """
    Fit a Gaussian function to the given 1D profile.

    Parameters:
        x (np.ndarray): 1D coordinate array.
        profile (np.ndarray): 1D intensity profile.
    
    Returns:
        popt (tuple): Optimal values for the parameters 
                      (amplitude, mean, sigma, offset).
        pcov (2D array): The estimated covariance of popt.
    """
    # Initial guess for the parameters:
    offset_guess = np.min(profile)
    amplitude_guess = np.max(profile) - offset_guess
    # Use the intensity-weighted mean as an initial guess for the mean.
    mean_guess = np.sum(x * profile) / np.sum(profile)
    # Estimate sigma from the weighted variance.
    sigma_guess = np.sqrt(np.sum(profile * (x - mean_guess)**2) / np.sum(profile))
    
    p0 = [amplitude_guess, mean_guess, sigma_guess, offset_guess]
    
    # Perform the curve fit.
    popt, pcov = curve_fit(gaussian, x, profile, p0=p0)
    return popt, pcov

def load_tif_folder(folder_path):
    """
    Load a folder of TIFF images into a 3D NumPy volume and interpolate along the z-axis 
    so that the voxel size becomes isotropic (pixel_size x pixel_size x pixel_size).

    Parameters:
        folder_path (str): Path to the folder containing TIFF images.
        pixel_size (float): Pixel size for the x and y dimensions (e.g., in micrometers).
        z_spacing (float): Spacing between slices in the z dimension (e.g., in micrometers).
        convert_gray (bool): If True and if the image has 3 channels, convert it to grayscale.

    Returns:
        volume_iso (np.ndarray): 3D volume with isotropic voxel dimensions.
    """
    # Get a sorted list of all .tif files in the folder
    file_list = sorted(glob.glob(os.path.join(folder_path, '*.tif')))
    if not file_list:
        raise ValueError(f"No TIFF images found in folder: {folder_path}")
    
    slices = []
    for filename in file_list:
        # Read the image
        img = imageio.imread(filename)

        slices.append(img)
    
    # Stack the 2D slices to create a 3D volume.
    volume = np.stack(slices, axis=0)  # volume.shape is (num_slices, height, width)

    return volume.shape, volume

def um_to_px(x):
    return (x / 0.268) + 512

def px_to_um(x):
    return (x - 512) * 0.268
# =============================================================================
#  PARAMETERS
# =============================================================================
#D:/Light_Sheet_Images/Data/2025-2-28 16_33_4 (268.0nm, 250ms, 24.41ms) - 488nm_Bead_200nm_Right_Iso
folder_path     = "D:/Light_Sheet_Images/Data/2025-2-28 16_33_4 (268.0nm, 250ms, 24.41ms) - 488nm_Bead_200nm_Right_Iso"  
# Update as needed
pixel_size      = 0.268  # Pixel size in x and y (in micrometers)
z_spacing       = 0.268    # Original spacing between z-slices (in micrometers)
# Define the size of the cube to extract (voxels)
sub_size        = 15
#sub_size_z      = 51
sub_size_z      = 51
# Threshold the normalized volume (adjust threshold_value as needed).
threshold_value = 0.25
add_synthetic_data = False #overlay synthetic bead data onto each bead, tests the analysis
show_each_bead  = True

df = pd.DataFrame(columns=['Bead number', 'Xpx', 'Ypx', 'Zpx', 'Xum', 'Yum', 'Zum', 'FWHMx', 'FWHMy', 'FWHMz'])

# Load and interpolate the volume to obtain isotropic voxels.
ori_vol_shape , volume_iso = load_tif_folder(folder_path)
print("Ori Volume shape (z, y, x):", ori_vol_shape)
print("ISO Volume shape (z, y, x):", volume_iso.shape)

# apply blur to remove noise
#volume_iso_blur = gaussian_filter(volume_iso, sigma=0.5)
volume_iso_blur = volume_iso
# subtract background
mean = np.mean(volume_iso_blur)
volume_iso_blur = volume_iso_blur - (mean/3)

# z-project whole stack
z_projection = np.sum(volume_iso_blur, axis=0)

aggregate_PSF = np.zeros((sub_size,sub_size,sub_size_z))

# =============================================================================
# Volume normalisation (naive)
# =============================================================================
max_val = np.max(volume_iso_blur) 
if max_val == 0:
    raise ValueError("The maximum intensity in the volume is zero, cannot normalize.")
iso_vol_norm = volume_iso_blur / max_val



# eliminate edge cases
# Calculate boundaries.
upper_z_limit = iso_vol_norm.shape[0] - sub_size_z // 2
lower_z_limit = sub_size_z // 2
upper_y_limit = iso_vol_norm.shape[1] - sub_size_z // 2
lower_y_limit = sub_size // 2
upper_x_limit = iso_vol_norm.shape[2] - sub_size_z // 2
lower_x_limit = sub_size // 2



# --- Visualization of Detected Beads ---
x_coords = np.arange(sub_size)
y_coords = np.arange(sub_size)
z_coords = np.arange(sub_size_z)


# =============================================================================
# bead detection
# =============================================================================
binary_mask = iso_vol_norm > threshold_value

# Label connected components in the binary mask. A 3x3x3 connectivity structure groups adjacent (including diagonal) voxels.
structure = np.ones((3, 3, 3), dtype=int)
labeled, num_features = label(binary_mask, structure=structure)
centers = center_of_mass(binary_mask, labeled, index=range(1, num_features + 1))
print(f"Number of beads detected: {num_features}")
    
# eliminate beads that are too close to an edge
n=0 
for b, bead_center in enumerate(centers, start=1): # find brightness
    zc, yc, xc = np.round(bead_center).astype(int)
    if(     zc > upper_z_limit or
            zc < lower_z_limit or
            yc > upper_y_limit or
            yc < lower_y_limit or
            xc > upper_x_limit or
            xc < lower_x_limit):
        continue
    

    z_start = int(zc - sub_size_z / 2)
    z_end   = int(zc + sub_size_z / 2)
    y_start = int(yc - sub_size / 2)
    y_end   = int(yc + sub_size / 2)
    x_start = int(xc - sub_size / 2)
    x_end   = int(xc + sub_size / 2)

# eliminate where multiple beads in the volume
    bead_cube_label = labeled[z_start:z_end, y_start:y_end, x_start:x_end]
    num_centers = len(np.unique(bead_cube_label))-1
    if(num_centers > 1):
        print('bead:', b, 'eliminated, (multiple beads in volume)')
        # continue
    
    bead_cube = iso_vol_norm[z_start:z_end, y_start:y_end, x_start:x_end]
    bead_cube_norm = bead_cube/np.max(bead_cube)
    
    
# binaraise the subvolume    
    bead_cube_bin = bead_cube_norm > 0.5
    volume = np.sum(bead_cube_bin)
    if(volume > 75):
        print('bead:', b, 'eliminated, (volume)', volume)
        # continue

# eliminate where brightest pixel not in xy center
    max_coords = np.argwhere(bead_cube_norm == 1)
    if(abs(max_coords[0][1] - sub_size/2) > 3 or
       abs(max_coords[0][1] - sub_size/2) > 3):
        print('bead:', b, 'eliminated, (brightest not centered)')
        # continue
        
# filter based on number of islands (beads)

    processed_arr_3d = fill_water_bridges_3D(bead_cube_bin)
    structure_3d = generate_binary_structure(3, 3)  # 3D array, full 26-connectivity
    labeled_array, num_islands = label(processed_arr_3d, structure=structure_3d)
    if(num_islands > 1):
        print('bead:', b, 'eliminated,', num_islands, 'islands')
        # continue   
    
    # print('bead:', b, 'added', n, '\t [ X:', xc, '\t Y:', yc, '\t Z:', zc, ']', max_coords[0])


    

# =============================================================================
# FWHM stuff
# =============================================================================
    try:
        crop_z_min = int((sub_size_z/2)-2)
        crop_z_max = int((sub_size_z/2)+3)
        crop_xy_min = int((sub_size/2)-4)
        crop_xy_max = int((sub_size/2)+5)
        profile_x = np.sum(bead_cube_norm[crop_z_min:crop_z_max, :, :], axis=(0, 1))  # sum over z and y, profile along x.
        profile_y = np.sum(bead_cube_norm[crop_z_min:crop_z_max, :, :], axis=(0, 2))  # sum over z and x, profile along y.
        profile_z = np.sum(bead_cube_norm[:,crop_xy_min:crop_xy_max,crop_xy_min:crop_xy_max], axis=(1, 2))  # sum over y and x, profile along z.
    
        popt_x, pcov_x = fit_gaussian_to_profile(x_coords, profile_x)
        popt_y, pcov_y = fit_gaussian_to_profile(y_coords, profile_y)
        popt_z, pcov_z = fit_gaussian_to_profile(z_coords, profile_z)
    except:
        print('bead:', b, 'eliminated, (fitting)')
        continue
    
    # evaluate fit in Z axis
    fitted_profile_z = gaussian(z_coords, *popt_z)

# Calculate the sum of squares of residuals (SS_res)
    SS_res = np.sum((profile_z - fitted_profile_z) ** 2)

# Calculate the total sum of squares (SS_tot)
    SS_tot = np.sum((profile_z - np.mean(profile_z)) ** 2)

# Calculate the R-squared value
    r_squared = 1 - (SS_res / SS_tot)

    if r_squared < 0.9:
        print("R-squared:", r_squared)
        # continue

# measure the FWHM in each axis
    FWHMx = 2 * np.sqrt(2 * np.log(2)) * popt_x[2] * pixel_size
    FWHMy = 2 * np.sqrt(2 * np.log(2)) * popt_y[2] * pixel_size
    FWHMz = 2 * np.sqrt(2 * np.log(2)) * popt_z[2] * pixel_size
    
    um_offset = int((volume_iso.shape[1] / 2) * pixel_size)
    um_offset_z = (ori_vol_shape[0] / 2) * z_spacing
    original_z = int((zc/volume_iso.shape[0]) * ori_vol_shape[0])
    data_point = [b,xc, yc, original_z, 
                  (xc*pixel_size)-um_offset, (yc*pixel_size)-um_offset, (zc*pixel_size)-um_offset_z,
                  FWHMx, FWHMy, FWHMz]
    
    if(FWHMx > 2.5 or FWHMy > 2.5): continue
    
    df.loc[len(df)] = data_point  
    n+=1
    # add bead to the aggregate PSF
    
    aggregate_PSF = aggregate_PSF + bead_cube
    
    if show_each_bead:
# Compute maximum intensity projections.
        xy_proj = np.max(bead_cube_norm, axis=0)  # Collapse the z-axis.
        xz_proj = np.max(bead_cube_norm, axis=1)  # Collapse the y-axis.
        yz_proj = np.max(bead_cube_norm, axis=2)  # Collapse the x-axis.

# Compute binary maximum intensity projections.
        bin_xy_proj = np.max(bead_cube_bin, axis=0)  # Collapse the z-axis.
        bin_xz_proj = np.max(bead_cube_bin, axis=1)  # Collapse the y-axis.
        bin_yz_proj = np.max(bead_cube_bin, axis=2)  # Collapse the x-axis.

# Plot the bead projections.

        fig, axes = plt.subplots(3, 3, figsize=(15, 15))
        fig.suptitle(f"Bead {b} Projections: X {xc}, Y {yc}, Z {zc}, R2: {r_squared}", fontsize=16)
        
        axes[0,0].imshow(xy_proj, cmap='gray')
        axes[0,0].set_title("XY Projection")
        axes[0,0].axis('off')
        
        axes[0,1].imshow(xz_proj, cmap='gray')
        axes[0,1].set_title("XZ Projection")
        axes[0,1].axis('off')
        
        axes[0,2].imshow(yz_proj, cmap='gray')
        axes[0,2].set_title("YZ Projection")
        axes[0,2].axis('off')
        
        axes[1,0].imshow(bin_xy_proj, cmap='gray')
        axes[1,0].set_title("binary XY Projection")
        axes[1,0].axis('off')
        
        axes[1,1].imshow(bin_xz_proj, cmap='gray')
        axes[1,1].set_title("binary XZ Projection")
        axes[1,1].axis('off')
        
        axes[1,2].imshow(bin_yz_proj, cmap='gray')
        axes[1,2].set_title("binary YZ Projection")
        axes[1,2].axis('off')
    
        axes[2,0].plot(x_coords, profile_x, 'b-', label='Data')
        axes[2,0].plot(x_coords, gaussian(x_coords, *popt_x), 'r--', label='Gaussian Fit')
        
        axes[2,1].plot(y_coords, profile_y, 'b-', label='Data')
        axes[2,1].plot(y_coords, gaussian(y_coords, *popt_y), 'r--', label='Gaussian Fit')
        
        axes[2,2].plot(z_coords, profile_z, 'b-', label='Data')
        axes[2,2].plot(z_coords, gaussian(z_coords, *popt_z), 'r--', label='Gaussian Fit')
        
        plt.tight_layout()
        plt.show()
   
print(n, 'beads identified')
# =============================================================================
# AGGREGATE BEAD
# =============================================================================
aggregate_PSF = aggregate_PSF / np.max(aggregate_PSF)

xy_proj = np.max(aggregate_PSF, axis=0)  # Collapse the z-axis.
xz_proj = np.max(aggregate_PSF, axis=1)  # Collapse the y-axis.
yz_proj = np.max(aggregate_PSF, axis=2)  # Collapse the x-axis.

try:
    crop_z_min = int((sub_size_z/2)-2)
    crop_z_max = int((sub_size_z/2)+3)
    crop_xy_min = int((sub_size/2)-4)
    crop_xy_max = int((sub_size/2)+5)
    profile_x = np.sum(bead_cube_norm[crop_z_min:crop_z_max, :, :], axis=(0, 1))  # sum over z and y, profile along x.
    profile_y = np.sum(bead_cube_norm[crop_z_min:crop_z_max, :, :], axis=(0, 2))  # sum over z and x, profile along y.
    profile_z = np.sum(bead_cube_norm[:,crop_xy_min:crop_xy_max,crop_xy_min:crop_xy_max], axis=(1, 2))  # sum over y and x, profile along z.

    popt_x, pcov_x = fit_gaussian_to_profile(x_coords, profile_x)
    popt_y, pcov_y = fit_gaussian_to_profile(y_coords, profile_y)
    popt_z, pcov_z = fit_gaussian_to_profile(z_coords, profile_z)

    # measure the FWHM in each axis
    FWHMx = 2 * np.sqrt(2 * np.log(2)) * popt_x[2] * pixel_size
    FWHMy = 2 * np.sqrt(2 * np.log(2)) * popt_y[2] * pixel_size
    FWHMz = 2 * np.sqrt(2 * np.log(2)) * popt_z[2] * pixel_size
    
    fig, axes = plt.subplots(2, 3, figsize=(10, 15))
    fig.suptitle("Aggregate bead Projections", fontsize=16)
    
    axes[0,0].imshow(xy_proj, cmap='gray')
    axes[0,0].set_title("XY Projection")
    axes[0,0].axis('off')
    
    axes[0,1].imshow(xz_proj, cmap='gray')
    axes[0,1].set_title("XZ Projection")
    axes[0,1].axis('off')
    
    axes[0,2].imshow(yz_proj, cmap='gray')
    axes[0,2].set_title("YZ Projection")
    axes[0,2].axis('off')
    
    axes[1,0].plot(x_coords, profile_x, 'b-', label='Data')
    axes[1,0].plot(x_coords, gaussian(x_coords, *popt_x), 'r--', label='Gaussian Fit')
    
    axes[1,1].plot(y_coords, profile_y, 'b-', label='Data')
    axes[1,1].plot(y_coords, gaussian(y_coords, *popt_y), 'r--', label='Gaussian Fit')
    
    axes[1,2].plot(z_coords, profile_z, 'b-', label='Data')
    axes[1,2].plot(z_coords, gaussian(z_coords, *popt_z), 'r--', label='Gaussian Fit')
    
    plt.tight_layout()
    plt.show()
except:
    print('bad fit')

# =============================================================================
# PLOTS
# =============================================================================
degree = 2

# FIT LINE X
coefficients = np.polyfit(df['Xum'], df['FWHMx'], degree)
polynomial = np.poly1d(coefficients)

# Generate x values for plotting the fitted polynomial
x_fit = np.linspace(df['Xum'].min(), df['Xum'].max(), 100)
y_fit = polynomial(x_fit)

# Plot the original scatter data and the polynomial fit
plt.scatter(df['Xum'], df['FWHMx'], label='FWHMx', color='blue')
plt.plot(x_fit, y_fit, label='Polynomial fit', color='red')
plt.xlabel('position (um)')
plt.ylabel('FWHM (um)')
plt.title('Polynomial Fit to Scatter Data')
plt.legend()
plt.show()

# FIT LINE Y
coefficients = np.polyfit(df['Yum'], df['FWHMy'], degree)
polynomial = np.poly1d(coefficients)

# Generate x values for plotting the fitted polynomial
x_fit = np.linspace(df['Yum'].min(), df['Yum'].max(), 100)
y_fit = polynomial(x_fit)

# Plot the original scatter data and the polynomial fit
plt.scatter(df['Yum'], df['FWHMy'], label='FWHMy', color='green')
plt.plot(x_fit, y_fit, label='Polynomial fit', color='red')
plt.xlabel('position (um)')
plt.ylabel('FWHM (um)')
plt.title('Polynomial Fit to Scatter Data')
plt.legend()
plt.show()

# FIT LINE Z
coefficients = np.polyfit(df['Zum'], df['FWHMz'], degree)
polynomial = np.poly1d(coefficients)

# Generate x values for plotting the fitted polynomial
x_fit = np.linspace(df['Zum'].min(), df['Zum'].max(), 100)
y_fit = polynomial(x_fit)

# Plot the original scatter data and the polynomial fit
plt.scatter(df['Zum'], df['FWHMz'], label='FWHMz', color='green')
plt.plot(x_fit, y_fit, label='Polynomial fit', color='red')
plt.xlabel('position (um)')
plt.ylabel('FWHM (um)')
plt.title('Polynomial Fit to Scatter Data')
plt.legend()
plt.show()

# Z projection of stack
fig, axes = plt.subplots(1, 1, figsize=(15, 15))
axes.imshow(z_projection, cmap='viridis')
axes.set_title("Z Projection")
plt.show()


# Color scatter plot XY
fig, ax = plt.subplots(figsize=(9, 6))
scatter = ax.scatter(df['Xum'], df['Yum'], c=df['FWHMx'], cmap='viridis', edgecolor='k')

# Labels and title
plt.xlabel("Xum")
plt.ylabel("Yum")
plt.xlim(-150, 150)  # Force x-axis limits
plt.ylim(150, -150)  # Force y-axis limits

# Create a secondary x-axis on the top for inches
secax_x = ax.secondary_xaxis('top', functions=(um_to_px, px_to_um))
secax_x.set_xlabel("X (px)")

# Create a secondary y-axis on the right for inches
secax_y = ax.secondary_yaxis('right', functions=(um_to_px, px_to_um))
secax_y.set_ylabel("Y (px)")

# Add colorbar
cbar = plt.colorbar(scatter)
cbar.set_label("FWHMx Value")

plt.title("Scatter Plot with FWHMx as Color")
plt.show()



