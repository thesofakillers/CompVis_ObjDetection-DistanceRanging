"""
functionality: perform detection based on HOG feature descriptor / SVM classification
using a very basic multi-scale, sliding window (exhaustive search) approach

This version: (c) 2018 Toby Breckon, Dept. Computer Science, Durham University, UK
License: MIT License

Minor portions: based on fork from https://github.com/nextgensparx/PyBOW

Original Module Docstring^^^^ I slightly edited the script so that I can use it
more modularly
"""
from T_Breckon.BoW_HOG.sliding_window import *
from T_Breckon.BoW_HOG.utils import *
import T_Breckon.BoW_HOG.params as params
import math


def hog_detect(image, rescaling_factor, svm_object, scan_boolean):
    output_img = image.copy();

    # for a range of different image scales in an image pyramid
    current_scale = -1
    detections = []

    ################################ for each re-scale of the image

    for resized in pyramid(image, scale=rescaling_factor):

        # at the start our scale = 1, because we catch the flag value -1
        if current_scale == -1:
            current_scale = 1

        # after this rescale downwards each time (division by re-scale factor)
        else:
            current_scale /= rescaling_factor

        rect_img = resized.copy()

        # if we want to see progress show each scale
        if (scan_boolean):
            cv2.imshow('current scale',rect_img)
            cv2.waitKey(10);

        # loop over the sliding window for each layer of the pyramid (re-sized image)
        window_size = params.DATA_WINDOW_SIZE
        step = math.floor(resized.shape[0] / 16)

        if step > 0:

            ############################# for each scan window

            for (x, y, window) in sliding_window(resized, window_size, step_size=step):

                # if we want to see progress show each scan window
                if (scan_boolean):
                    cv2.imshow('current window',window)
                    key = cv2.waitKey(10) # wait 10ms

                # for each window region get the HoG feature point descriptors
                img_data = ImageData(window)
                img_data.compute_hog_descriptor();

                # generate and classify each window by constructing a HoG
                # histogram and passing it through the SVM classifier
                if img_data.hog_descriptor is not None:

                    print("detecting with SVM ...")

                    retval, [result] = svm_object.predict(np.float32([img_data.hog_descriptor]))

                    print(result)

                    # if we get a detection, then record it
                    if result[0] == params.DATA_CLASS_NAMES["pedestrain"]:

                        # store rect as (x1, y1) (x2,y2) pair
                        rect = np.float32([x, y, x + window_size[0], y + window_size[1]])

                        # if we want to see progress show each detection, at each scale
                        if (scan_boolean):
                            cv2.rectangle(rect_img, (rect[0], rect[1]), (rect[2], rect[3]), (0, 0, 255), 2)
                            cv2.imshow('current scale',rect_img)
                            cv2.waitKey(40)

                        #append the rect to the list of detections

                        rect *= (1.0 / current_scale)
                        detections.append(rect)

            ########################################################

    # For the overall set of detections (over all scales) perform
    # non maximal suppression (i.e. remove overlapping boxes etc).
    detections = non_max_suppression_fast(np.int32(detections), 0.4)

    return detections
