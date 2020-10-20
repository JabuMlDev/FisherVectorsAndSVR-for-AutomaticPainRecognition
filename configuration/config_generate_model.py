import numpy as np
"""Configuration file for the generate_model_predictor.py script that allows you to generate
a certain model predictor from its parameters"""

n_kernels_GMM = 50   # Number of clusters of the GMM

threshold_neutral = 0.3  # Defines the threshold of the neutral configurations
""" If the threshold is 0.3, all those configurations that occur within the sequences with vas equal to 0 
 with a frequency greater than 0.3 will be considered neutral """
selected_lndks_idx = [5, 11, 19, 24, 37, 41, 56, 58] # Indexes of the landmarks to use for fitting GMM and description sequences

train_by_max_score = True  # Defines whether the model classifier must be generated by maximizing the
                           # resulting score as the gamma and regularization

regularization_parameter = 1  # Only to be used if train_by_max_score = False

gamma_parameter = 'scale'  # Only to be used if train_by_max_score = False

type_classifier = 'SVR'  # Indicates the type of the classifier ('SVR' or 'SVM')

save_histo_figures = True  # Defines if the histograms of the dataset sequences must be saved in their respective files
"""If save_histo_figures = True, the histograms are saved in the project folder
 'data/classifier/n_kernels/figures/histograms/' with n=number of kernels of GMM
 (make sure that this file exists)"""

cross_val_protocol = "5-fold-cross-validation"  # Define type of protocol to be used to evaluate the performance of the models
"""cross_val_protocol:  'Leave-One-Sequence-Out' or '5-fold-cross-validation' """
