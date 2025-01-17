"""
functionality: utility functions for shared usage across different scripts

Largely Based on work by: (c) 2018 Toby Breckon, Dept. Computer Science,
Durham University, UK
License: MIT License

Origin acknowledgements: forked from https://github.com/nextgensparx/PyBOW
"""

# <section>~~~~~~~~~~~~~~~~~~~~~~~~~~Imports~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os
import numpy as np
import cv2
import SVM.params as params
import math
import random
import colorsys
# </section>End of Imports


# <section>~~~~~~~~~~~~~~~~~~~~~~~~Global Flags~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
show_additional_process_information = False
show_images_as_they_are_loaded = False
show_images_as_they_are_sampled = False
# </section>End of Global Flags


# <section>~~~~~~~~~~~~~~~~~~~~~~~~~~Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#   <section>~~~~~~~~~~~~~~Timing Functions By T Breckon~~~~~~~~~~~~~~~~~~~~~~~~
def get_elapsed_time(start):
    return (cv2.getTickCount() - start) / cv2.getTickFrequency()


def format_time(time):
    time_str = ""
    if time < 60.0:
        time_str = "{}s".format(round(time, 1))
    elif time > 60.0:
        minutes = time / 60.0
        time_str = "{}m : {}s".format(int(minutes), round(time % 60, 2))
    return time_str


def print_duration(start):
    time = get_elapsed_time(start)
    print(("Took {}".format(format_time(time))))
#   </section>End of Timing

#   <section>~~~~~~~~~~~~~~~~~Image Handling Functions~~~~~~~~~~~~~~~~~~~~~~~~~~


def read_all_images(path): #TBreckon
    """
    reads all the images in a given folder path and returns the list containing
    them. Will break with a very large datasets due to memory issues
    """
    images_path = [os.path.join(path, f) for f in os.listdir(path)]
    images = []
    for image_path in images_path:
        img = cv2.imread(image_path)

        if show_additional_process_information:
            print("loading file - ", image_path)

        images.append(img)
    return images


def load_image_path(path, class_name, imgs_data, samples=0, centre_weighting=False, centre_sampling_offset=10, patch_size=(64, 128)): #TBreckon
    """
    add images from a specified path to the dataset, adding the appropriate
    class/type name and optionally adding up to N samples of a specified size with
    flags for taking them from the centre of the image only with +/- offset in pixels
    """

    # read all images at location
    imgs = read_all_images(path)

    img_count = len(imgs_data)
    for img in imgs:

        if (show_images_as_they_are_loaded):
            cv2.imshow("example", img)
            cv2.waitKey(5)

        # generate up to N sample patches for each sample image
        # if zero samples is specified then generate_patches just returns
        # the original image (unchanged, unsampled) as [img]
        for img_patch in generate_patches(img, samples, centre_weighting, centre_sampling_offset, patch_size):

            if show_additional_process_information:
                print("path: ", path, "class_name: ",
                      class_name, "patch #: ", img_count)
                print("patch: ", patch_size, "from centre: ",
                      centre_weighting, "with offset: ", centre_sampling_offset)

            # add each image patch to the data set

            img_data = ImageData(img_patch)
            img_data.set_class(class_name)
            imgs_data.insert(img_count, img_data)
            img_count += 1

    return imgs_data


def load_images(paths, class_names, sample_set_sizes, use_centre_weighting_flags, centre_sampling_offset=10, patch_size=(64, 128)): #TBreckon
    """load image data from specified paths"""

    imgs_data = []  # type: list[ImageData]

    # for each specified path and corresponding class_name and required number
    # of samples - add them to the data set

    for path, class_name, sample_count, centre_weighting in zip(paths, class_names, sample_set_sizes, use_centre_weighting_flags):
        load_image_path(path, class_name, imgs_data, sample_count,
                        centre_weighting, centre_sampling_offset, patch_size)

    return imgs_data


def crop_image(image, start_height, end_height, start_width, end_width):
    """
    Crops an image according to passed start and end heights and widths with
    the origin placed at the image top left
    """
    return image[start_height:end_height, start_width:end_width]


def select_roi_maintain_size(image, start_height=0, start_width=0):
    """
    Essentially crops the image, but the shape remains the same. Cropped out areas
    are simply filled in with black. This is to accomodate openCV's Sel. Search
    """
    # copying the image so to avoid editing the originalù
    copy = np.copy(image)
    # cropping vertically
    copy[0:start_height, :] = 0
    # cropping horizontally
    copy[:, 0:start_width] = 0
    return copy
#   </section>End of Image Handling

#   <section>~~~~~~~~~~~~~~~~~Class Transform Functions~~~~~~~~~~~~~~~~~~~~~~~~~


def get_class_number(class_name): #TBreckon
    return params.DATA_CLASS_NAMES.get(class_name, 0)


def get_class_name(class_code): #TBreckon
    for name, code in params.DATA_CLASS_NAMES.items():
        if code == class_code:
            return name


def get_class_labels(imgs_data):
    class_labels = [img_data.class_number for img_data in imgs_data]
    return np.int32(class_labels)
#   </section>End of Class Transforms Functions

#   <section>~~~~~~~~~~~~~~~~~~~~~~Depth Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def compute_depth(disparity, focal_length, distance_between_cameras):
    """
    Computes depth in meters
    Input:
    -Disparity in pixels
    -Focal Length in pixels
    -Distance between cameras in meters
    Output:
    -Depth in meters
    """
    with np.errstate(divide='ignore'): #ignore division by 0
        # standard depth and disparity formula
        depth = (focal_length * distance_between_cameras) / disparity
    return depth


def compute_single_depth(rectangle, disparity_image, focal_length, distance_between_cameras):
    """
    Given a rectangular area and a disparity image, estimates the general Depth
    of that rectangular ROI
    """
    # extracting corners from rectangle (top left and bottom right)
    x1, y1, x2, y2 = rectangle
    # cropping and flattening disparity image so that we are only dealing with ROI values
    rectangle_disparity = crop_image(disparity_image, y1, y2, x1, x2)
    # sorting the disparity ROI by ascending disparity
    rectangle_disparity = np.sort(rectangle_disparity, axis=None)
    # keeping only the final third of the pixels (which we believe correspond to the detected object)
    rectangle_disparity = rectangle_disparity[(
        2 * len(rectangle_disparity)) // 3:]
    # compute corresponding depths
    rectangle_depths = compute_depth(
        rectangle_disparity, focal_length, distance_between_cameras)
    # return the average depth
    return np.average(rectangle_depths)
#   </section> End of Depth Functions

#   <section>~~~~~~~~~~~~~~~~~Miscelleanous Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~


def gen_N_colors(N):
    """
    Input: integer N describing the number of desired distinct colors
    Output: List of tuples representing N distinct colors in BGR space
    """
    # get unique colors from hsv space and convert to rgb
    rgb_colors = [colorsys.hsv_to_rgb(h, np.random.random(), 0.85)
                  for h in np.linspace(0, 1, N)]
    # convert to bgr
    bgr_colors = np.fliplr(rgb_colors)
    # shuffle
    np.random.shuffle(bgr_colors)
    # return unnormalized array
    return 255*bgr_colors


def stack_array(arr): #TBreckon
    stacked_arr = np.array([])
    for item in arr:
        # Only stack if it is not empty
        if len(item) > 0:
            if len(stacked_arr) == 0:
                stacked_arr = np.array(item)
            else:
                stacked_arr = np.vstack((stacked_arr, item))
    return stacked_arr


def generate_patches(img, sample_patches_to_generate=0, centre_weighted=False,
                     centre_sampling_offset=10, patch_size=(64, 128)): #TBreckon
    """
    generates a set of random sample patches from a given image of a specified size
    with an optional flag just to train from patches centred around the centre of the image
    """
    patches = []

    # if no patches specifed just return original image

    if (sample_patches_to_generate == 0):
        return [img]

    # otherwise generate N sub patches

    else:

        # get all heights and widths

        img_height, img_width, _ = img.shape
        patch_height = patch_size[1]
        patch_width = patch_size[0]

        # iterate to find up to N patches (0 -> N-1)

        for patch_count in range(sample_patches_to_generate):

            # if we are using centre weighted patches, first grab the centre patch
            # from the image as the first sample then take the rest around centre

            if (centre_weighted):

                # compute a patch location in centred on the centre of the image

                patch_start_h = math.floor(
                    img_height / 2) - math.floor(patch_height / 2)
                patch_start_w = math.floor(
                    img_width / 2) - math.floor(patch_width / 2)

                # for the first sample we'll just keep the centre one, for any
                # others take them from the centre position +/- centre_sampling_offset
                # in both height and width position

                if (patch_count > 0):
                    patch_start_h = random.randint(
                        patch_start_h - centre_sampling_offset, patch_start_h + centre_sampling_offset)
                    patch_start_w = random.randint(
                        patch_start_w - centre_sampling_offset, patch_start_w + centre_sampling_offset)

                # print("centred weighted path")

            # else get patches randonly from anywhere in the image

            else:

                # print("non centred weighted path")

                # randomly select a patch, ensuring we stay inside the image

                patch_start_h = random.randint(0, (img_height - patch_height))
                patch_start_w = random.randint(0, (img_width - patch_width))

            # add the patch to the list of patches

            patch = img[patch_start_h:patch_start_h + patch_height,
                        patch_start_w:patch_start_w + patch_width]

            # show image patches

            if (show_images_as_they_are_sampled):
                cv2.imshow("patch", patch)
                cv2.waitKey(5)

            patches.insert(patch_count, patch)

        return patches


def get_hog_descriptors(imgs_data): #TBreckon
    """return the global set of hog descriptors for the data set of images"""
    samples = stack_array([[img_data.hog_descriptor]
                           for img_data in imgs_data])
    return np.float32(samples)


def non_max_suppression_fast(boxes, overlapThresh): #TBreckon
    """
    perform basic non-maximal suppression of overlapping object detections
    """
    # if there are no boxes, return an empty list
    if len(boxes) == 0:
        return []

    # if the bounding boxes integers, convert them to floats --
    # this is important since we'll be doing a bunch of divisions
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    # initialize the list of picked indexes
    pick = []

    # grab the coordinates of the bounding boxes
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    # compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)

    # keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the
        # index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # find the largest (x, y) coordinates for the start of
        # the bounding box and the smallest (x, y) coordinates
        # for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # compute the ratio of overlap
        overlap = (w * h) / area[idxs[:last]]

        # delete all indexes from the index list that have a significant overlap
        idxs = np.delete(idxs, np.concatenate(([last],
                                               np.where(overlap > overlapThresh)[0])))

    # return only the indices of bounding boxes that were picked using the
    # integer data type
    return pick


def area_depth_heuristic(height, width, pixel_height, pixel_width, distance, focal_length, mush_factor):
    """
    Returns whether the area_depth_heuristic is satisfied. Specifically, if a detected region is of small area,
    then it is expected to be far away and viceversa. This function compares the area with the measured stereo
    depth.

    Inputs:
    -height, width: real height and width of what is being observed
    -pixel_height, pixel_width: height and width of observed object in image
    -distance: measured stereo distance to the object in meters
    -focal_length: camera focal length in pixels
    -mush_factor: how much leeway to give in comparing. Usually between 0 and 1

    Outputs:
    -Boolean: True if satisfied, False if else.
    """
    # expected area occupied by an object with passed size at passed distance
    expected_area = (height * width * focal_length**2) / distance**2
    # observed area
    observed_area = pixel_width * pixel_height
    # heuristic
    if observed_area < (1 - mush_factor) * expected_area or observed_area > (1.2 + mush_factor) * expected_area:
        return False
    else:
        return True
#   </section>End of Miscelleanous

# </section>End of Functions


# <section>~~~~~~~~~~~~~~~~~~~~~~~~~~Classes~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class ImageData(object): #TBreckon
    """image data class object that contains the images, descriptors and bag of word
    histograms"""

    def __init__(self, img):
        self.img = img
        self.class_name = ""
        self.class_number = None
        self.initialize_HoG_Descriptor()
        self.hog_descriptor = np.array([])

    def initialize_HoG_Descriptor(self,
                                  win_size=params.HOG_DESC_winSize,
                                  block_size=params.HOG_DESC_blockSize,
                                  block_stride=params.HOG_DESC_blockStride,
                                  cell_size=params.HOG_DESC_cellSize,
                                  n_bins=params.HOG_DESC_nbins,
                                  deriv_aperture=params.HOG_DESC_derivAperture,
                                  window_sigma=params.HOG_DESC_winSigma,
                                  norm_type=params.HOG_DESC_histogramNormType,
                                  L2_threshold=params.HOG_DESC_L2HysThreshold,
                                  gamma_corr=params.HOG_DESC_gammaCorrection):
        """
        initializes the HoGDescriptor Object
        """
        self.hog = cv2.HOGDescriptor(win_size,
                                     block_size,
                                     block_stride,
                                     cell_size,
                                     n_bins,
                                     deriv_aperture,
                                     window_sigma,
                                     norm_type,
                                     L2_threshold,
                                     gamma_corr)

    def set_class(self, class_name):
        self.class_name = class_name
        self.class_number = get_class_number(self.class_name)
        if show_additional_process_information:
            print("class name : ", class_name, " - ", self.class_number)

    def compute_hog_descriptor(self):
        """
        computes the HOG descriptors for a given image
        """

        # # resizes the image to ensure that all images are the same size.
        img_hog = cv2.resize(
            self.img, (params.DATA_WINDOW_SIZE[0], params.DATA_WINDOW_SIZE[1]), interpolation=cv2.INTER_AREA)

        # computes hog descriptor utilizing built-in openCV
        self.hog_descriptor = self.hog.compute(img_hog)

        if self.hog_descriptor is None:
            self.hog_descriptor = np.array([])

        if show_additional_process_information:
            print("HOG descriptor computed - dimension: ",
                  self.hog_descriptor.shape)
# </section>End of Classes
