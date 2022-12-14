import pickle
import numpy as np
import pandas as pd
from fishervector import FisherVectorGMM
from sklearn.preprocessing import RobustScaler
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')



class PreliminaryClustering:
    """Class that is responsible for obtaining the relevant configurations for the classification of the VAS index. """

    def __init__(self, coord_df_path, seq_df_path, num_lndks, selected_lndks_idx, train_video_idx, n_kernels,
                 threshold_neutral, covariance_type='diag', verbose=True, fit_by_bic=False):
        self.coord_df_path = coord_df_path  # Path of csv file contained coordinates of the landmarks
        self.seq_df_path = seq_df_path  # Path of csv file contained sequences informations
        self.num_lndks = num_lndks  # Number of landmarks for each frame of the videos in the dataset
        self.selected_lndks_idx = selected_lndks_idx  # Indexes of the landmarks to considered to the clustering
        self.train_video_idx = train_video_idx  # Indexes of the videos to use for training
        self.fit_by_bic = fit_by_bic  # Define if the GMM must be fitted using fit by bic
        self.threshold_neutral = threshold_neutral  # Thresholds to use fo extraction of the neutral configurations
        self.n_kernels = n_kernels  # Number of kernels of the gmm to trained
        self.covariance_type = covariance_type  # type of the covariance matrix to use for the GMM fitting
        self.verbose = verbose  # define if the output must be printed in the class
        self.gmm = None  # GMM fitted using fisherVector module on the training features
        self.fisher_vectors = None  # FV of the frames contained in dataset
        self.histograms_of_videos = None  # histograms of all sequences contained in dataset
        self.index_relevant_configurations = None  # indexes of the clusters to considered as relevant
        self.index_neutral_configurations = None  # indexes of the clusters to considered as neutral (not to use for VAS classification)

    def __get_velocities_frames(self):
        """
        Extract velocities of landmarks video sequences in dataset.
        Return a list of 2D array with velocities of the landmarks for each frame
        """

        if self.verbose:
            print("---- Calculating velocities of the frames in dataset... ----")
        coord_df = pd.read_csv(self.coord_df_path)
        seq_df = pd.read_csv(self.seq_df_path)
        velocities = []
        for seq_num in np.arange(seq_df.shape[0]):
            lndks = coord_df.loc[coord_df['0'] == seq_num].values
            lndks = lndks[:, 2:]
            nose_tip_x = lndks[:, 30]
            nose_tip_y = lndks[:, 30 + self.num_lndks]
            offset = np.hstack((np.repeat(nose_tip_x.reshape(-1, 1), self.num_lndks, axis=1),
                                np.repeat(nose_tip_y.reshape(-1, 1), self.num_lndks, axis=1)))
            lndks_centered = lndks - offset
            lndk_vel = np.power(np.power(lndks_centered[0:lndks_centered.shape[0] - 1, 0:self.num_lndks] -
                                         lndks_centered[1:lndks_centered.shape[0], 0:self.num_lndks], 2) +
                                np.power(lndks_centered[0:lndks_centered.shape[0] - 1, self.num_lndks:] -
                                         lndks_centered[1:lndks_centered.shape[0], self.num_lndks:], 2),
                                0.5)
            data_velocities = []
            for k in np.arange(1, lndk_vel.shape[0]):
                data_velocities.append(np.array(lndk_vel[k, self.selected_lndks_idx]))
            velocities.append(np.array(data_velocities))
        return velocities

    def __scale_features(self, velocities):
        """
        Scaling the features using RobustScaler. It makes features more robust than the outliers
        """

        if self.verbose:
            print("---- Scaling the features... ----")
        train_velocities = [velocities[i] for i in self.train_video_idx]
        features_train_frames = np.array([feature_frame for feature_video in train_velocities for feature_frame in feature_video])
        features_all_frames = np.array([feature_frame for feature_video in velocities for feature_frame in feature_video])
        features_all_frames = RobustScaler().fit(features_train_frames).transform(features_all_frames)
        feat_count = 0
        for video_idx, feature_video in enumerate(velocities):
            for frame_idx, feature_frame_idx in enumerate(feature_video):
                velocities[video_idx][frame_idx][:] = features_all_frames[feat_count]
                feat_count += 1
        return velocities

    def __prepare_training_features(self, velocities):
        """
        Prepare features for GMM training.
        All velocities of the sequences frame are inserted in a 4D array that contains all frames informations.
        Features of the frames of all videos are collected in the same sequence.
        Return a 4D array with velocities of the landmarks for each frame in the dataset
        """

        if self.verbose:
            print("---- Preparing features vector of the frame in the training set by velocities... ----")
        train_velocities = [velocities[i] for i in self.train_video_idx]
        train_num_frames = sum([video.shape[0] for video in train_velocities])
        n_features_for_frame = len(self.selected_lndks_idx)
        train_frames_features = np.ndarray(shape=(1, train_num_frames, 1, n_features_for_frame))
        index_frame = 0
        for video_idx in self.train_video_idx:
            video = velocities[video_idx]
            for frame_idx in np.arange(video.shape[0]):
                current_frame_features = video[frame_idx]
                train_frames_features[0][index_frame][0][:] = current_frame_features[:]
                index_frame += 1
        return train_frames_features

    def __generate_gmm(self, train_frames_features):
        """
        Train Gaussian Mixture for process fisher vectors.
        Return the fitted GMM
        """

        if self.fit_by_bic:
            if self.verbose:
                print("---- Generate GMM with fitting by BIC... ----")
            gmm = FisherVectorGMM(covariance_type=self.covariance_type).fit_by_bic(
                X=train_frames_features, choices_n_kernels=self.n_kernels, verbose=self.verbose)
            n_kernels_current_GMM = len(gmm.means)
            if self.fit_by_bic and isinstance(self.threshold_neutral, list):
                self.threshold_neutral = self.threshold_neutral[self.n_kernels.index(n_kernels_current_GMM)]
            self.n_kernels = n_kernels_current_GMM
            return gmm
        else:
            if self.verbose:
                print("---- Generate GMM with " + str(self.n_kernels) + " kernels... ----")
            return FisherVectorGMM(n_kernels=self.n_kernels, covariance_type=self.covariance_type).fit(
                X=train_frames_features, verbose=False)

    def __calculate_FV(self, velocities):
        """
        Calculate the fisher vectors of the first num test videos of the dataset.
        Return the calculated fisher vectors
        """

        if self.verbose:
            print("---- Calculate fisher vectors of video sequences in dataset... ----")
        n_features_for_frame = len(self.selected_lndks_idx)
        fisher_vectors = []
        for feature in velocities:
            fv = self.gmm.predict(np.array(feature).reshape(1, feature.shape[0], 1, n_features_for_frame))
            fisher_vectors.append(fv)
        return fisher_vectors

    def __generate_histograms(self):
        """
        Calculate the histograms of the videos starting from the fisher vectors of the frames.
        Uses the clustering method to establish the cluster of a sequence by his fisher vector.
        Return a list with histograms of videos
        """

        if self.verbose:
            print("---- Generate histograms of video sequences... ----")
        histograms_of_videos = []
        for video_fv in self.fisher_vectors:
            current_video_fv = video_fv[0]
            video_histogram = np.zeros(self.n_kernels)
            for frame in current_video_fv:
                for index_configuration in range(0, self.n_kernels):
                    video_histogram[index_configuration] += sum(frame[index_configuration]) + \
                                                            sum(frame[index_configuration + self.n_kernels])
            video_histogram = video_histogram / sum(video_histogram)
            histograms_of_videos.append(video_histogram)
        return histograms_of_videos

    def __extract_relevant_and_neutral_configurations(self):
        """
        Apply a strategy to derive the relevant and neutral configurations for classify the VAS index using histograms.
        Return two lists containing respectively the indices of the relevant and neutral configurations to classify
        the vas index
        """

        if self.verbose:
            output = "---- Extracts relevant and neutral configurations analyzing train sequences"
            if self.threshold_neutral != None:
                output += " (with threshold=" + str(
                    self.threshold_neutral) +")"
            output += "... ----"
            print(output)
        seq_df = pd.read_csv(self.seq_df_path)
        index_neutral_configurations = []
        for seq_num in self.train_video_idx:
            vas = seq_df.iloc[seq_num][1]
            if vas == 0:
                hist = self.histograms_of_videos[seq_num]
                for j in np.arange(self.n_kernels):
                    if hist[j] > self.threshold_neutral and j not in index_neutral_configurations:
                        index_neutral_configurations.append(j)
        index_relevant_configurations = [x for x in np.arange(self.n_kernels) if x not in index_neutral_configurations]
        return index_relevant_configurations, index_neutral_configurations

    def __plot_and_save_histograms(self, histo_figures_path):
        """
        Plot and save histograms by distinguishing the color of the representations of the relevant configurations
        from the neutral ones
        """

        if self.verbose:
            print("---- Plot and save histograms... ----")
        for idx, histo in enumerate(self.histograms_of_videos):
            if len(self.index_neutral_configurations):
                plt.bar(self.index_neutral_configurations, histo[np.array(self.index_neutral_configurations)], color="blue")
            if len(self.index_relevant_configurations):
                plt.bar(self.index_relevant_configurations, histo[np.array(self.index_relevant_configurations)],color="red")
            plt.title("VIDEO #" + str(idx))
            plt.savefig(histo_figures_path + 'video-%03d.png' % idx, dpi=200)
            plt.close()

    def execute_preliminary_clustering(self, preliminary_clustering_dump_path=None,
                                       histo_figures_path=None):
        """
        Execute preliminary clustering using the parameters passed to class constructor.
        If plot_and_save_histo is setted on True value the figures of histograms of videos is saved in files
        """

        velocities = self.__get_velocities_frames()
        velocities_scaled = self.__scale_features(velocities)
        train_frames_features = self.__prepare_training_features(velocities_scaled)
        self.gmm = self.__generate_gmm(train_frames_features)
        self.fisher_vectors = self.__calculate_FV(velocities_scaled)
        self.histograms_of_videos = self.__generate_histograms()
        self.index_relevant_configurations, self.index_neutral_configurations = \
            self.__extract_relevant_and_neutral_configurations()
        if histo_figures_path is not None:
            self.__plot_and_save_histograms(histo_figures_path)
        if preliminary_clustering_dump_path is not None:
            self.__dump_on_pickle(preliminary_clustering_dump_path)

    def __dump_on_pickle(self, preliminary_clustering_dump_path):
        with open(preliminary_clustering_dump_path, 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load_from_pickle(pickle_path):
        with open(pickle_path, 'rb') as f:
            preliminary_clustering = pickle.load(f)
            assert isinstance(preliminary_clustering, PreliminaryClustering)
        return preliminary_clustering
