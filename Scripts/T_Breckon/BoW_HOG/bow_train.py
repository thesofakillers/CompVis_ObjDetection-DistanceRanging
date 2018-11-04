################################################################################

# functionality: perform all stages of Bag of (visual) Words (BoW) training over
# a specified dataset and compute the resulting prediction/clasification error
# over that same dataset, having saved the SVM model to file for subsequent re-use

# This version: (c) 2018 Toby Breckon, Dept. Computer Science, Durham University, UK
# License: MIT License

# Origin acknowledgements: forked from https://github.com/nextgensparx/PyBOW

################################################################################

import cv2
from utils import *

################################################################################

def generate_dictionary(imgs_data, dictionary_size):

    # Extracting descriptors
    desc = stack_array([img_data.bow_descriptors for img_data in imgs_data])

    # important, cv2.kmeans() clustering only accepts type32 descriptors

    desc = np.float32(desc)

    # perform clustering - increase iterations and reduce EPS to change performance

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, params.BOW_clustering_iterations, 0.01)
    flags = cv2.KMEANS_PP_CENTERS

    # desc is a type32 numpy array of vstacked descriptors

    compactness, labels, dictionary = cv2.kmeans(desc, dictionary_size, None, criteria, 1, flags)
    np.save(params.BOW_DICT_PATH, dictionary)

    return dictionary

################################################################################

def main():

    ############################################################################
    # load our training data set of images examples

    program_start = cv2.getTickCount()

    print("Loading images...")
    start = cv2.getTickCount()

    # N.B. specify data path names in same order as class names (neg, pos)

    paths = [params.DATA_training_path_neg, params.DATA_training_path_pos]

    # build a lisyt of class names automatically from our dictionary of class (name,number) pairs

    class_names = [get_class_name(class_number) for class_number in range(len(params.DATA_CLASS_NAMES))]

    # specify number of sub-window samples to take from each positive and negative
    # example image in the data set
    # N.B. specify in same order as class names (neg, pos) - again

    sampling_sizes = [params.DATA_training_sample_count_neg, params.DATA_training_sample_count_pos]

    # do we want to take samples only centric to the example image or ramdonly?
    # No - for background -ve images (first class)
    # Yes - for object samples +ve images (second class)

    sample_from_centre = [False, True];

    # perform image loading

    imgs_data = load_images(paths, class_names, sampling_sizes, sample_from_centre,
                            params.DATA_WINDOW_OFFSET_FOR_TRAINING_SAMPLES, params.DATA_WINDOW_SIZE);

    print(("Loaded {} image(s)".format(len(imgs_data))))
    print_duration(start)

    ############################################################################
    # perform bag of visual words feature construction

    print("Computing descriptors...") # for each training image
    start = cv2.getTickCount()
    [img_data.compute_bow_descriptors() for img_data in imgs_data]
    print_duration(start)

    print("Clustering...")          # over all images to generate dictionary code book/words
    start = cv2.getTickCount()
    dictionary = generate_dictionary(imgs_data, params.BOW_dictionary_size)
    print_duration(start)

    print("Generating histograms...") # for each training image
    start = cv2.getTickCount()
    [img_data.generate_bow_hist(dictionary) for img_data in imgs_data]
    print_duration(start)

    ############################################################################
    # train an SVM based on these norm_features

    print("Training SVM...")
    start = cv2.getTickCount()

    # define SVM parameters

    svm = cv2.ml.SVM_create()
    svm.setType(cv2.ml.SVM_C_SVC)           # change this for multi-class
    svm.setKernel(params.BOW_SVM_kernel)    # use specific kernel type (alteratives exist)

    # compile samples (i.e. visual word histograms) for each training image

    samples = get_bow_histograms(imgs_data)

    # get class label for each training image

    class_labels = get_class_labels(imgs_data);

    # specify the termination criteria for the SVM training

    svm.setTermCriteria((cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, params.BOW_SVM_max_training_iterations, 1.e-06))

    # perform auto training for the SVM which will essentially perform grid
    # search over the set of parameters for the chosen kernel and the penalty
    # cost term, C (N.B. trainAuto() syntax is correct as of OpenCV 3.4.x)

    svm.trainAuto(samples, cv2.ml.ROW_SAMPLE, class_labels, kFold = 10, balanced = True);

    # save the tained SVM to file so that we can load it again for testing / detection

    svm.save(params.BOW_SVM_PATH)

    ############################################################################
    # measure performance of the SVM trained on the bag of visual word features

    # perform prediction over the set of examples we trained over

    output = svm.predict(samples)[1].ravel()
    error = (np.absolute(class_labels.ravel() - output).sum()) / float(output.shape[0])

    # we are succesful if our prediction > than random
    # e.g. for 2 class labels this would be 1/2 = 0.5 (i.e. 50%)

    if error < (1.0 / len(params.DATA_CLASS_NAMES)):
        print("Trained SVM obtained {}% training set error".format(round(error * 100,2)))
        print("-- meaining the SVM got {}% of the training examples correct!".format(round((1.0 - error) * 100,2)))
    else:
        print("Failed to train SVM. {}% error".format(round(error * 100,2)))

    print_duration(start)

    print(("Finished training BOW detector. {}".format(format_time(get_elapsed_time(program_start)))))

################################################################################

if __name__ == '__main__':
    main()

################################################################################
