import matplotlib
matplotlib.use('Agg')

# Import stuff!
import numpy as np
import tables
import easygui
import sys
import os
from blech_hmm import *
import pylab as plt

# Read blech.dir, and cd to that directory
f = open('blech.dir', 'r')
dir_name = []
for line in f.readlines():
	dir_name.append(line)
f.close()
os.chdir(dir_name[0][:-1])

# Pull out the NSLOTS - number of CPUs allotted
#n_cpu = int(os.getenv('NSLOTS'))
n_cpu = int(sys.argv[1])

# Get the names of all files in the current directory, and find the .hmm_params, .hmm_units and hdf5 (.h5) file
file_list = os.listdir('./')
hdf5_name = ''
params_file = ''
units_file = ''
for files in file_list:
	if files[-2:] == 'h5':
		hdf5_name = files
	if files[-10:] == 'hmm_params':
		params_file = files
	if files[-9:] == 'hmm_units':
		units_file = files

# Read the .hmm_params file
f = open(params_file, 'r')
params = []
for line in f.readlines():
	params.append(line)
f.close()

# Assign the params to variables
min_states = int(params[0])
max_states = int(params[1])
threshold = float(params[2])
seeds = int(params[3])
edge_inertia = float(params[4])
dist_inertia = float(params[5])
taste = int(params[6])
pre_stim = int(params[7])
bin_size = int(params[8])
pre_stim_hmm = int(params[9])
post_stim_hmm = int(params[10])
hmm_type = params[11][:-1]

# Read the chosen units
f = open(units_file, 'r')
chosen_units = []
for line in f.readlines():
	chosen_units.append(int(line))
chosen_units = np.array(chosen_units)

# Open up hdf5 file
hf5 = tables.open_file(hdf5_name, 'r+')

# Get the spike array from the required taste/input
exec('spikes = hf5.root.spike_trains.dig_in_%i.spike_array[:]' % taste)

# Slice out the required portion of the spike array, and bin it (only use the units in chosen_units)
spikes = spikes[:, chosen_units, pre_stim - pre_stim_hmm:pre_stim + post_stim_hmm]
binned_spikes = np.zeros((spikes.shape[0], spikes.shape[1], int((pre_stim_hmm + post_stim_hmm)/bin_size)))
time = []
for i in range(spikes.shape[0]):
	time = []
	for k in range(0, spikes.shape[2], bin_size):
		time.append(k - pre_stim_hmm)
		binned_spikes[i, :, int(k/bin_size)] = np.sum(spikes[i, :, k:k+bin_size], axis = 1)
# Now reshape binned_spikes so that its shaped n_trials x time x n_units
binned_spikes = np.swapaxes(binned_spikes, 1, 2)

# Implement a Poisson HMM for no. of states defined by min_states and max_states - run all the trials through the HMM
hmm_results = []
off_trials = np.arange(binned_spikes.shape[0])
for n_states in range(min_states, max_states + 1):
	# Run the Poisson HMM - skip if it doesn't converge for some reason
	try:
		result = poisson_hmm_implement(n_states, threshold, seeds, n_cpu, binned_spikes, off_trials, edge_inertia, dist_inertia, hmm_type)
		hmm_results.append((n_states, result))
	except: 
		continue

# Delete the poisson_hmm_results node under /spike_trains/dig_in_(taste)/ if it exists
try:
	hf5.remove_node('/spike_trains/dig_in_%i/%s_poisson_hmm_results' % (taste, hmm_type), recursive = True)
except:
	pass

# Then create the poisson_hmm_results group, and save the identities of the chosen units to this group
hf5.create_group('/spike_trains/dig_in_%i/' % taste, '%s_poisson_hmm_results' % hmm_type)
# hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/' % (taste, hmm_type), 'chosen_units', chosen_units)
hf5.flush()

# Delete the Poisson folder within HMM_plots if it exists for this taste
try:
	os.system("rm -r ./HMM_plots/dig_in_%i/%s_Poisson" % (taste, hmm_type))
except:
	pass	

# Make a folder for plots of Poisson HMM analysis
os.mkdir("HMM_plots/dig_in_%i/%s_Poisson" % (taste, hmm_type))

# Go through the HMM results, and make plots for each state and each trial
for result in hmm_results:
	# Make a directory for this number of states
	os.mkdir("HMM_plots/dig_in_%i/%s_Poisson/states_%i" % (taste, hmm_type, result[0]))
		
	# Make a group under poisson_hmm_results for this number of states
	hf5.create_group('/spike_trains/dig_in_%i/%s_poisson_hmm_results' % (taste, hmm_type), 'states_%i' % (result[0])) 
	# Write the emission and transition probabilties to this group
	emission_probs = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'emission_probs', result[1][4])
	transition_probs = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'transition_probs', result[1][5])
	posterior_proba = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'posterior_proba', result[1][6])

	# Also write the json model string to file
	# model_json = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'model_json', result[1][0])

	# Write the log-likelihood, AIC/BIC score, and time vector to the hdf5 file too
	log_prob = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'log_likelihood', np.array(result[1][1]))
	aic = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'aic', np.array(result[1][2]))
	bic = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'bic', np.array(result[1][3]))
	time_vect = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/states_%i' % (taste, hmm_type, result[0]), 'time', time)
	hf5.flush()

	# Go through the trials in binned_spikes and plot the trial-wise posterior probabilities with the unit rasters
	# First make a dictionary of colors for the rasters
	raster_colors = {'regular_spiking': 'red', 'fast_spiking': 'blue', 'multi_unit': 'black'}
	for i in range(binned_spikes.shape[0]):
		fig = plt.figure()
		for j in range(posterior_proba.shape[2]):
			plt.plot(time, binned_spikes.shape[2]*posterior_proba[i, :, j])
		for unit in range(binned_spikes.shape[2]):
			# Determine the type of unit we are looking at - the color of the raster will depend on that
			if hf5.root.unit_descriptor[chosen_units[unit]]['regular_spiking'] == 1:
				unit_type = 'regular_spiking'
			elif hf5.root.unit_descriptor[chosen_units[unit]]['fast_spiking'] == 1:
				unit_type = 'fast_spiking'
			else:
				unit_type = 'multi_unit'
			for j in range(spikes.shape[2]):
				if spikes[i, unit, j] > 0:
					plt.vlines(j - pre_stim_hmm, unit, unit + 0.5, color = raster_colors[unit_type], linewidth = 0.5)
		plt.xlabel('Time post stimulus (ms)')
		plt.ylabel('Probability of HMM states' + '\n' + 'Unit number')
		plt.title('Trial %i' % (i+1) + '\n' + 'RSU: red, FS: blue, Multi: black')
		fig.savefig('HMM_plots/dig_in_%i/%s_Poisson/states_%i/Trial_%i.png' % (taste, hmm_type, result[0], (i+1)))
		plt.close("all")

# Check if the laser_array exists - if it does, perform a 2nd round of HMM training on just the non-laser trials
exec('dig_in = hf5.root.spike_trains.dig_in_%i' % taste)
laser_exists = []
try:
	laser_exists = dig_in.laser_durations[:]
except:
	pass
if len(laser_exists) > 0:
	on_trials = np.where(dig_in.laser_durations[:] > 0.0)[0]
	off_trials = np.where(dig_in.laser_durations[:] == 0.0)[0]
	# Implement a Poisson HMM for no. of states defined by min_states and max_states
	hmm_results = []
	for n_states in range(min_states, max_states + 1):
		# Run the Poisson HMM - skip it if it doesn't converge
		try:
			result = poisson_hmm_implement(n_states, threshold, seeds, n_cpu, binned_spikes, off_trials, edge_inertia, dist_inertia, hmm_type)
			hmm_results.append((n_states, result))
		except:
			continue

	# Delete the laser node under /spike_trains/dig_in_(taste)/poisson_hmm_results/ if it exists
	try:
		exec("hf5.remove_node('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser' % (taste, hmm_type), recursive = True)")
	except:
		pass

	# Then create the poisson_hmm_results group
	exec("hf5.create_group('/spike_trains/dig_in_%i/%s_poisson_hmm_results' % (taste, hmm_type), 'laser')")
	hf5.flush()

	# Delete the laser folder within HMM_plots/Poisson if it exists for this taste
	try:
		os.system("rm -r ./HMM_plots/dig_in_%i/%s_Poisson/laser" % (taste, hmm_type))
	except:
		pass	

	# Make a folder for plots of Poisson HMM analysis
	os.mkdir("HMM_plots/dig_in_%i/%s_Poisson/laser" % (taste, hmm_type))
	
	# Go through the HMM results, and make plots for each state and each trial
	for result in hmm_results:
		
		# Make a directory for this number of states
		os.mkdir("HMM_plots/dig_in_%i/%s_Poisson/laser/states_%i" % (taste, hmm_type, result[0]))
		
		# Make a group under poisson_hmm_results for this number of states
		hf5.create_group('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser' % (taste, hmm_type), 'states_%i' % (result[0])) 
		# Write the emission and transition probabilties to this group
		emission_probs = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'emission_probs', result[1][4])
		transition_probs = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'transition_probs', result[1][5])
		posterior_proba = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'posterior_proba', result[1][6])

		# Also write the json model string to file
		# model_json = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'model_json', result[1][0])

		# Write the log-likelihood and AIC/BIC score to the hdf5 file too
		log_prob = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'log_likelihood', np.array(result[1][1]))
		aic = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'aic', np.array(result[1][2]))
		bic = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'bic', np.array(result[1][3]))
		time_vect = hf5.create_array('/spike_trains/dig_in_%i/%s_poisson_hmm_results/laser/states_%i' % (taste, hmm_type, result[0]), 'time', time)
		hf5.flush()

		# Go through the trials in binned_spikes and plot the trial-wise posterior probabilities and raster plots
		# First make a dictionary of colors for the rasters
		raster_colors = {'regular_spiking': 'red', 'fast_spiking': 'blue', 'multi_unit': 'black'}
		for i in range(binned_spikes.shape[0]):
			if i in on_trials:
				label = 'laser_on_'
			else:
				label = 'laser_off_'
			fig = plt.figure()
			for j in range(posterior_proba.shape[2]):
				plt.plot(time, binned_spikes.shape[2]*posterior_proba[i, :, j])
			for unit in range(binned_spikes.shape[2]):
				# Determine the type of unit we are looking at - the color of the raster will depend on that
				if hf5.root.unit_descriptor[chosen_units[unit]]['regular_spiking'] == 1:
					unit_type = 'regular_spiking'
				elif hf5.root.unit_descriptor[chosen_units[unit]]['fast_spiking'] == 1:
					unit_type = 'fast_spiking'
				else:
					unit_type = 'multi_unit'
				for j in range(spikes.shape[2]):
					if spikes[i, unit, j] > 0:
						plt.vlines(j - pre_stim_hmm, unit, unit + 0.5, color = raster_colors[unit_type], linewidth = 0.5)
			plt.xlabel('Time post stimulus (ms)')
			plt.ylabel('Probability of HMM states' + '\n' + 'Unit number')
			plt.title('Trial %i, Dur: %ims, Lag: %ims' % (i+1, dig_in.laser_durations[i], dig_in.laser_onset_lag[i]) + '\n' + 'RSU: red, FS: blue, Multi: black')
			fig.savefig('HMM_plots/dig_in_%i/%s_Poisson/laser/states_%i/%sTrial_%i.png' % (taste, hmm_type, result[0], label, (i+1)))
			plt.close("all")
		
hf5.close()	

	
