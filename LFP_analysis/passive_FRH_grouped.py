#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  3 13:48:08 2019

@author: bradly
"""

# import Libraries
# Built-in Python libraries
import os # functions for interacting w operating system
import sys # access to functions/variables at the level of the interpreter

#import operator tools for list manipulations
from itertools import groupby
from operator import itemgetter

# 3rd-party libraries
import numpy as np # module for low-level scientific computing
import scipy as sp # library for working with NumPy arrays
import scipy.io as sio # read/write data to various formats
from scipy import signal # signal processing module
import matplotlib.pyplot as plt # makes matplotlib work like MATLAB. ’pyplot’ functions.
from scipy import stats
from statsmodels.sandbox.stats.multicomp import multipletests
from scipy.stats import sem  
import easygui
import tables
import pickle #for data storage and retreival

# Define SEM function for smoothing figures (they are messy because so long)
def sliding_mean(data_array, window=5):  
    data_array = np.array(data_array)  
    new_list = []  
    for i in range(len(data_array)):  
        indices = range(max(i - window + 1, 0),  
                        min(i + window + 1, len(data_array)))  
        avg = 0  
        for j in indices:  
            avg += data_array[j]  
        avg /= float(len(indices))  
        new_list.append(avg)  
          
    return np.array(new_list)  

#Get name of directory where you want to save output files to
save_name = easygui.diropenbox(msg = 'Choose directory you want output files sent to (and/or where ".dir" files are)',default = '/home/bradly/drive2/data/Affective_State_Protocol/LiCl/Combined_Passive_Data/grand_analyses')

#Ask user if they have ran set-up before
msg   = "Have you performed directory set-up before (ie. do you have '.dir' files in output folder) ?"
dir_check = easygui.buttonbox(msg,choices = ["Yes","No"])

if dir_check == "No":
    #Get data_saving name
    msg   = "What condition are you analyzing first?"
    subplot_check1 = easygui.buttonbox(msg,choices = ["Saline","LiCl","Other"])
    
    # Ask the user for the hdf5 files that need to be plotted together (fist condition)
    dirs_1 = []
    while True:
    	dir_name = easygui.diropenbox(msg = 'Choose first condition directory with a hdf5 file, hit cancel to stop choosing')
    	try:
    		if len(dir_name) > 0:	
    			dirs_1.append(dir_name)
    	except:
    		break   
    
    # Ask the user for the hdf5 files that need to be plotted together (second condition)
    #Get data_saving name
    msg   = "What condition are you analyzing second?"
    subplot_check2 = easygui.buttonbox(msg,choices = ["Saline","LiCl","Other"])
    
    dirs_2 = []
    while True:
    	dir_name = easygui.diropenbox(msg = 'Choose second condition directory with a hdf5 file, hit cancel to stop choosing')
    	try:
    		if len(dir_name) > 0:	
    			dirs_2.append(dir_name)
    	except:
    		break
    
    #Dump the directory names into chosen output location for each condition
    #condition 1
    completeName_1 = os.path.join(save_name, 'dirs_cond1.dir') 
    f_1 = open(completeName_1, 'w')
    for item in dirs_1:
        f_1.write("%s\n" % item)
    f_1.close()
    
    #condition 2
    completeName_2 = os.path.join(save_name, 'dirs_cond2.dir') 
    f_2 = open(completeName_2, 'w')
    for item in dirs_2:
        f_2.write("%s\n" % item)
    f_2.close()

if dir_check == "Yes":
    
    #Get data_saving name
    msg   = "What condition are you analyzing first?"
    subplot_check1 = easygui.buttonbox(msg,choices = ["Saline","LiCl","Other"])
    
    #establish directories to flip through
    #condition 1
    dirs_1_path = os.path.join(save_name, 'dirs_cond1.dir')
    dirs_1_file = open(dirs_1_path,'r')
    dirs_1 = dirs_1_file.read().splitlines()
    dirs_1_file.close()
    
    #Get data_saving name
    msg   = "What condition are you analyzing second?"
    subplot_check2 = easygui.buttonbox(msg,choices = ["Saline","LiCl","Other"])
    
    #condition 2
    dirs_2_path = os.path.join(save_name, 'dirs_cond2.dir')
    dirs_2_file = open(dirs_2_path,'r')
    dirs_2 = dirs_2_file.read().splitlines()
    dirs_2_file.close()
    
#modify save names
if subplot_check1==subplot_check2:
    subplot_check2=subplot_check2+'_2'    
	
# Get the psth paramaters from the user
params = easygui.multenterbox(msg = 'Enter the parameters for making firing rate spreads', fields = ['Pre stimulus (ms)','Window size (ms)', 'Step size (ms)','Smoothing Spline (1-10; 5 is conservative)'],values = ['0','10000','5000','5'])
for i in range(len(params)):
	params[i] = int(params[i])

#Get name of directory where the data files and hdf5 file sits, and change to that directory for processing
dirs_animals_1 = [[]for x in range(2)]; dirs_animals_2 = [[]for x in range(2)]; #Create 2D list to store animal IDs and unit counts

#Ask user about held units anlysis and perform analyses as seen fit
msg   = "Do you want to include a held cell analyses?"
held_check = easygui.buttonbox(msg,choices = ["Yes","No"])
if held_check == "Yes":
	held_dir_name = easygui.diropenbox(msg = 'Choose directory with all "_held_units.txt" files in it.',default = '/home/bradly/drive2/data/Affective_State_Protocol/LiCl/Combined_Passive_Data/grand_analyses')
	
	#Create empty arrays for storing FRH later
	#held_FRs_cond1 = []; held_FRs_cond2 = []; 
	held_FRs_cond1_2 = []; held_FRs_cond2_2 = []
	
	#Flip through all files and create a held_units list
	for file in held_dir_name:
		#Change to the directory
		os.chdir(held_dir_name)
		#Locate the hdf5 file
		file_list = os.listdir('./')
		held_file_name = ''

		day1 =[]; day2=[]; #Create arrays for each day
		all_day1=[]; all_day2=[] #Create arrays for combined days
		for files in sorted(file_list):
			if files[-3:] == 'txt':

				with open(files,'r') as splitfile:
					for columns in [line.split() for line in splitfile]:
						day1.append(columns[0]);	day2.append(columns[1])
					all_day1.append(day1); all_day2.append(day2)
					day1 = []; day2 = []    #Clear day array
					
	#Remove 'Day' from all lists
	for sublist in all_day1:
	    del sublist[0]
		
	for sublist in all_day2:
	    del sublist[0]
		
	#Account for out of order units
	sorted_day1 = [];sorted_day2=[]
	for animal in range(np.size(all_day1)):
		sorted_day1.append(sorted(all_day1[animal], key=int))
		sorted_day2.append(sorted(all_day2[animal], key=int))
										
#Flip through directories and obtain spike train info					
dirs_1_spike_rates =[];dirs_2_spike_rates =[]; 
dirs_count = 0 #start directory count for hend_unit analyses
for dir_name in dirs_1:
	#Change to the directory
	os.chdir(dir_name)
	#Locate the hdf5 file
	file_list = os.listdir('./')
	hdf5_name = ''
	for files in file_list:
		if files[-2:] == 'h5':
			hdf5_name = files
			
	#Open the hdf5 file
	hf5 = tables.open_file(hdf5_name, 'r')
	    
	# Get the list of spike trains by digital input channels
	trains_dig_in = hf5.list_nodes('/spike_trains')
	
	# Plot FRHs by unit and channels
	for dig_in in trains_dig_in:
		trial_avg_spike_array = np.mean(dig_in.spike_array[:], axis = 0)
		unit_count= 0 #start hed unit count
		dumunit=0
		for unit in range(trial_avg_spike_array.shape[0]):
			time = []
			spike_rate = []
			for i in range(0, trial_avg_spike_array.shape[1] - params[1], params[2]):
				time.append(i - params[0])
				spike_rate.append(1000.0*np.sum(trial_avg_spike_array[unit, i:i+params[1]])/float(params[1]))
			dirs_1_spike_rates.append(spike_rate)
			
			if held_check == "Yes":
				sorted_day1 = sorted(all_day1[dirs_count], key=int)		
				if unit == int(sorted_day1[dumunit]):
					held_FRs_cond1_2.append(spike_rate)
					if dumunit<np.size(sorted_day1)-1:
						dumunit+=1

    	#Append animal number and unit count to list
	dirs_animals_1[0].append(hdf5_name[:4])
	dirs_animals_1[1].append(trial_avg_spike_array.shape[0])
	
	#Close the hdf5 file
	hf5.close()	
	
	#Increase count
	dirs_count+=1

#Flip through second condition
dirs_count = 0 #start directory count for hend_unit analyses	
for dir_name in dirs_2:
	#Change to the directory
	os.chdir(dir_name)
	#Locate the hdf5 file
	file_list = os.listdir('./')
	hdf5_name = ''
	for files in file_list:
		if files[-2:] == 'h5':
			hdf5_name = files

	#Open the hdf5 file
	hf5 = tables.open_file(hdf5_name, 'r')
    
	# Get the list of spike trains by digital input channels
	trains_dig_in = hf5.list_nodes('/spike_trains')
	
	# Plot FRHs by unit and channels
	for dig_in in trains_dig_in:
		trial_avg_spike_array = np.mean(dig_in.spike_array[:], axis = 0)
		unit_count= 0 #start hed unit count
		dumunit=0
		for unit in range(trial_avg_spike_array.shape[0]):
			time = []
			spike_rate = []
			for i in range(0, trial_avg_spike_array.shape[1] - params[1], params[2]):
				time.append(i - params[0])
				spike_rate.append(1000.0*np.sum(trial_avg_spike_array[unit, i:i+params[1]])/float(params[1]))
			dirs_2_spike_rates.append(spike_rate)
			
			if held_check == "Yes":
				sorted_day2 = sorted(all_day2[dirs_count], key=int)		
				if unit == int(sorted_day2[dumunit]):
					held_FRs_cond2_2.append(spike_rate)
					if dumunit<np.size(sorted_day2)-1:
						dumunit+=1
			
    	#Append animal number and unit count to list
	dirs_animals_2[0].append(hdf5_name[:4])
	dirs_animals_2[1].append(trial_avg_spike_array.shape[0])		

    #Close the hdf5 file
	hf5.close()
	
	#Increase count
	dirs_count+=1

#Begin plotting loop
fig = plt.figure( figsize=(10, 8))
unit_1_start = 0; unit_2_start = 0
for animal, cond1_units, cond2_units in zip(dirs_animals_1[0],dirs_animals_1[1],dirs_animals_2[1]):
	
	#Plot change in sliding means
	plt.plot(time, (sliding_mean(np.mean(dirs_2_spike_rates[unit_2_start:unit_2_start+cond2_units-1],axis=0),window=params[3])-sliding_mean(np.mean(dirs_1_spike_rates[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]))/sliding_mean(np.mean(dirs_1_spike_rates[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]),label=animal)
	
	#Update unit start counts	
	unit_1_start += cond1_units
	unit_2_start += cond2_units

#Mean of all animals
all_anmimals_1 = sliding_mean(np.mean(dirs_1_spike_rates,axis=0),window=params[3])
all_anmimals_2 = sliding_mean(np.mean(dirs_2_spike_rates,axis=0),window=params[3])

#Format figure
plt.axhline(0, linestyle='--', color='grey', linewidth=2)
plt.plot(time,(all_anmimals_2-all_anmimals_1)/all_anmimals_1, linestyle=':', color='black', linewidth=4)
plt.title('Firing Rate Histogram' +'\n' + 'Animals: %i, Window: %i ms, Step: %i ms' % (np.size(dirs_animals_1[0]),params[1], params[2]) + '\n' + 'Condition 1 Units: %i, Condition 2 Units: %i, Smoothing Spline: %ith order' % (np.size(dirs_1_spike_rates,axis=0),np.size(dirs_2_spike_rates,axis=0), params[3]))
plt.xlabel('Time from injection (ms)')
plt.ylabel(r'$\Delta$'+ ' Firing rate (Hz)')
plt.legend()

#Save figure
fig.savefig(save_name+'/All_animals_%i_Smoothed_%ims_window.png' % (np.size(dirs_animals_1[0]),params[1]))
plt.close('all')

#Perform same plotting, but on held cells only
if held_check == "Yes":
	#Establish number of held units per animal
	held_units_final = []
	for animal in range(np.size(all_day1)):
		held_units_final.append(np.size(all_day1[animal]))
	
	#Begin plotting loop
	fig = plt.figure( figsize=(10, 8))
	unit_1_start = 0; 
	for animal, cond1_units in zip(dirs_animals_1[0],held_units_final[:]):
		
		#Plot change in sliding means
		if cond1_units==1:
			plt.plot(time, (sliding_mean(np.mean(held_FRs_cond2_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3])-sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3]))/sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3]),label=animal)
		else:
			plt.plot(time, (sliding_mean(np.mean(held_FRs_cond2_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3])-sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]))/sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]),label=animal)
		
		#Update unit start counts	
		unit_1_start += cond1_units

	#Mean of all animals
	all_anmimals_1 = sliding_mean(np.mean(held_FRs_cond1_2,axis=0),window=params[3])
	all_anmimals_2 = sliding_mean(np.mean(held_FRs_cond2_2,axis=0),window=params[3])
	change_scored = (all_anmimals_2-all_anmimals_1)/all_anmimals_1
	sem_change_scored = (sem(held_FRs_cond2_2,axis=0)-sem(held_FRs_cond1_2,axis=0))/sem(held_FRs_cond1_2,axis=0)
	
	#Format figure
	plt.axhline(0, linestyle='--', color='grey', linewidth=2)
	plt.plot(time,change_scored, linestyle=':', color='black', linewidth=4)
	plt.title('Held Unit Firing Rate Histogram' +'\n' + 'Animals: %i, Window: %i ms, Step: %i ms' % (np.size(dirs_animals_1[0]),params[1], params[2]) + '\n' + 'Units: %i, Smoothing Spline: %ith order' % (np.size(held_FRs_cond1_2,axis=0), params[3]))
	plt.xlabel('Time from injection (ms)')
	plt.ylabel(r'$\Delta$'+ ' Firing rate (Hz)')
	plt.legend()		

	#Save figure
	fig.savefig(save_name+'/Held_all_animals_%i_Smoothed_%ims_window.png' % (np.size(dirs_animals_1[0]),params[1]))
	
# =============================================================================
# =============================================================================
# # 	#Begin plotting loop ZSCORED
# =============================================================================
# =============================================================================
	norm_set_cond1=[];norm_set_cond2=[]
	for animal, cond1_units in zip(dirs_animals_1[0],held_units_final[:]):
	
		#Plot change in sliding means
		for unit in range(cond1_units):
			norm_set_cond1.append((held_FRs_cond1_2[unit] - np.mean(held_FRs_cond1_2[unit],axis=0))/np.std(held_FRs_cond1_2[unit]))
			norm_set_cond2.append((held_FRs_cond2_2[unit] - np.mean(held_FRs_cond2_2[unit],axis=0))/np.std(held_FRs_cond2_2[unit]))
	
	plt.plot(time,np.mean(norm_set_cond1,axis=0));plt.plot(time,np.mean(norm_set_cond2,axis=0))
	###START HERE####

	
	fig = plt.figure( figsize=(10, 8))
	unit_1_start = 0; 
	for animal, cond1_units in zip(dirs_animals_1[0],held_units_final[:]):
		
		#Plot change in sliding means
		if cond1_units==1:
			plt.plot(time, (sliding_mean(np.mean(held_FRs_cond2_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3])-sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3]))/sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units],axis=0),window=params[3]),label=animal)
		else:
			plt.plot(time, (sliding_mean(np.mean(held_FRs_cond2_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3])-sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]))/sliding_mean(np.mean(held_FRs_cond1_2[unit_1_start:unit_1_start+cond1_units-1],axis=0),window=params[3]),label=animal)
		
		#Update unit start counts	
		unit_1_start += cond1_units

	#Mean of all animals
	all_anmimals_1 = sliding_mean(np.mean(norm_set_cond1,axis=0),window=params[3])
	all_anmimals_2 = sliding_mean(np.mean(norm_set_cond2,axis=0),window=params[3])
	change_scored = all_anmimals_2-all_anmimals_1
	sem_change_scored = (sem(norm_set_cond2,axis=0)-sem(norm_set_cond1,axis=0))/sem(norm_set_cond1,axis=0)
	
	#Format figure
	plt.axhline(0, linestyle='--', color='grey', linewidth=2)
	plt.plot(time,change_scored, linestyle=':', color='black', linewidth=4)
	plt.title('Held Unit Firing Rate Histogram' +'\n' + 'Animals: %i, Window: %i ms, Step: %i ms' % (np.size(dirs_animals_1[0]),params[1], params[2]) + '\n' + 'Units: %i, Smoothing Spline: %ith order' % (np.size(held_FRs_cond1_2,axis=0), params[3]))
	plt.xlabel('Time from injection (ms)')
	plt.ylabel(r'$\Delta$'+ ' Firing rate (Hz)')
	plt.legend()		

	#Save figure
	fig.savefig(save_name+'/Held_all_animals_%i_Smoothed_%ims_window.png' % (np.size(dirs_animals_1[0]),params[1]))
	
# =============================================================================
# =============================================================================
# # 	
# =============================================================================
# =============================================================================
    #Creat ttest and pval vectors for storing outputs
	T_vector=[]; p_vector = []; 
	hFR1 = np.array(held_FRs_cond1_2); hFR2 = np.array(held_FRs_cond2_2) #convert lists to arrays
	
	#Perform dependent ttests for each bin
	for bin_num in range(np.size(hFR2,axis=1)):
		T,pval = stats.ttest_rel(hFR1[:,bin_num],hFR2[:,bin_num])
		T_vector.append(T); p_vector.append(pval)
	
	#Locate significant bins			
	sig_bins = list(np.where(np.array(p_vector) <= 0.05))		
	
	#Plot	
	fig = plt.figure( figsize=(10, 8))
	plt.axhline(0, linestyle='--', color='grey', linewidth=2)
	plt.plot(time,change_scored, linestyle=':', color='black', linewidth=4)
	plt.fill_between(time, change_scored - sem_change_scored,  
		                 change_scored + sem_change_scored, color="grey",alpha=0.3,label='SEM')
	plt.plot(time,change_scored,'rD',markevery=sig_bins,label='p < 0.05')	
	plt.title('Held Unit Firing Rate Histogram' +'\n' + 'Animals: %i, Window: %i ms, Step: %i ms' % (np.size(dirs_animals_1[0]),params[1], params[2]) + '\n' + 'Units: %i, Smoothing Spline: %ith order' % (np.size(held_FRs_cond1_2,axis=0), params[3]))
	plt.xlabel('Time from injection (ms)')
	plt.ylabel(r'$\Delta$'+ ' Firing rate (Hz)')
	plt.legend()
	
	#Save figure
	fig.savefig(save_name+'/Held_Stats_Smoothed_%ims_window.png' % (params[1]))
	
	#Plot	
	fig = plt.figure( figsize=(10, 8))
	plt.axhline(0, linestyle='--', color='grey', linewidth=2)
	plt.plot(time,change_scored, linestyle=':', color='black', linewidth=4)
	plt.plot(time,change_scored,'rD',markevery=sig_bins,label='p < 0.05')	
	plt.title('Held Unit Firing Rate Histogram' +'\n' + 'Animals: %i, Window: %i ms, Step: %i ms' % (np.size(dirs_animals_1[0]),params[1], params[2]) + '\n' + 'Units: %i, Smoothing Spline: %ith order' % (np.size(held_FRs_cond1_2,axis=0), params[3]))
	plt.xlabel('Time from injection (ms)')
	plt.ylabel(r'$\Delta$'+ ' Firing rate (Hz)')
	plt.legend()
	
	#Save figure
	fig.savefig(save_name+'/Held_Stats_Smoothed_%ims_window_noSEM.png' % (params[1]))
plt.close('all')

#Save necessary outputs to list in pickle
pickle_name = 'Cond_%s_Cond_%s_FRH.pkl' %(subplot_check1,subplot_check2)

#create keys
keys = ['condition','animals','held_cells','FRs_binned','t_vals','p_vals','time']

#cond 1 dictionary
values = [subplot_check1,dirs_animals_1,held_units_final,held_FRs_cond1_2,T_vector,p_vector,time]
d1 = dict(zip(keys,values))

#cond 2 dictionary
values = [subplot_check2,dirs_animals_2,held_units_final,held_FRs_cond2_2,T_vector,p_vector,time]
d2 = dict(zip(keys,values))

#combine dictionaries
new_dict = {}
new_dict[subplot_check1]=d1; new_dict[subplot_check2]=d2

#put into dump file
tuple_save = subplot_check1+ '_' +subplot_check2 + '_tuple.dump'
output_name =   os.path.join(save_name, tuple_save)
pickle.dump(new_dict, open(output_name, 'wb'))  








