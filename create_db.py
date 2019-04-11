'''
Given a path with folders containing images of people faces, this script
creates a pandas HDF file that can be inputed to another tool that permits
selecting proper photos for face recognition systems validation.

@author Luis Miguel Rojas Aguilera rojas@icomp.ufam.edu.br

'''


import argparse
import pandas as pd
from PIL import Image
import os
import time

def create_file(photos_path, output_path, min_size=300):
    print("Starting photos taggin tool db construction ...")
    previous_dataframe = None

    if os.path.exists(output_path):
        print("Loading existing data ...")
        previous_dataframe = pd.read_hdf(output_path)

    classes = os.listdir(photos_path)
    ccount = 1
    tia = 0
    cols = ['class', 'image_name', 'use_photo', 'width', 'height']
    for _class in classes:
        print("Processing class {}. [{}/{}]".format(_class, ccount, len(classes)))
        class_path = os.path.join(photos_path, _class)
        data = []
        ic = 0
        images_names = os.listdir(class_path)
        tiac = 0
        for image_name in images_names:
            ic += 1
            if previous_dataframe is not None:
                if not previous_dataframe[(previous_dataframe['class'] == _class)
                                      & (previous_dataframe['image_name'] ==
                                         image_name)].empty:
                    tia += 1
                    tiac += 1
                    print("\tData for image already in dataset, skipping ...")
                    continue

            image_path = os.path.join(class_path, image_name)
            w, h = 0, 0
            with Image.open(image_path) as i:
                w, h = i.size

            print("\tImage [{}/{}], Class [{}/{}]".format(ic,
                                                          len(images_names),
                                                          ccount, len(classes)))
            if w < min_size or h < min_size:
                print("\t\tDimensions ({}x{}) shorter than min_size {} skipping ...".format(w, h, min_size))
                continue

            data.append([_class, image_name, -1, w, h])
            tia += 1
            tiac += 1
            print("\t\tAdded. Per class: {}/{}, Total: {}".format(tiac,
                                                                len(images_names),
                                                               tia))

        d = pd.DataFrame(columns=cols, data=data)
        d.to_hdf(output_path, 'main', append=True, format='table')
        ccount += 1


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("dataset_address", help="Path with images")
    argp.add_argument("-s", "--image-min-size", help="Images should be at least this parameter value large in size (with and height). Default is 300x300", default=300, type=int)
    argp.add_argument("-o", "--output", help="Database output full path, including db file name. A name is created by default",
                      default="./facephoto_taggin_{}.h5".format("_".join(time.asctime().split())),
                      type=str)

    args = vars(argp.parse_args())
    create_file(args['dataset_address'], args['output'], args['image_min_size'])

