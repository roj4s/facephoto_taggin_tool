import argparse
from queue import Queue
import pandas as pd
from threading import Thread, Event
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop

TAG = "[TagginToolWebServer]"

def dataset_update_worker(dataset_addr, update_query_q, stop_event):
    tag = '[UpdateWorker]'
    while not stop_event.is_set():
        query = update_query_q.get()
        d = pd.read_hdf(dataset_addr)
        print("{} Got new query. Class: {}, Image {}, Use: {}".format(tag,
                                                                      query['class'],
                                                                     query['image_name'],
                                                                     query['use_photo']))

        d.loc[(d['class'] == query['class']) & (d['image_name'] == query['image_name']), 'use_photo'] = int(query['use_photo'])
        d.to_hdf(dataset_addr, 'main')
    print("Stopping updater worker ...")

def resolve_image_name(df, max_count, starting_class=None):
    while True:
        if starting_class is None:
            starting_class = df[df.use_photo == -1].sample(1)['class'].iloc[0]

        not_tagged_yet = df[(df['class'] == starting_class) & (df['use_photo']
                                                              == -1)]
        if not_tagged_yet.empty:
            print("\tAll images of class {} are already tagged...".format(starting_class))
            starting_class = None
            continue

        tagged_already = df[(df['class'] == starting_class) & (df['use_photo']
                                                              != -1)]

        if max_count != -1 and tagged_already.count()[0] >= max_count:
            print("\tClass {} has already {} tagged images ...".format(starting_class, max_count))
            starting_class = None
            continue

        return not_tagged_yet.sample(1)[['class', 'image_name']].values[0]

def all_images_tagged(df):
    return df[df.use_photo == -1].empty

def all_classes_has_min_items_tagged(df, count):
    tagged_by_class = df[df.use_photo != -1].groupby('class')
    return tagged_by_class.filter(lambda x: len(x) < count).empty

class ProvidePhotoHandler(RequestHandler):

    def check_origin(self, origin):
        return True

    def initialize(self, dataset_addr, images_url, max_count=30):
        self.images_url = images_url
        self.dataset_addr = dataset_addr
        self.max_count = max_count

    def get(self):
        _class = self.get_body_argument("class", None)

        print("Finding new photo ... ")
        df = pd.read_hdf(self.dataset_addr)
        max_count = -1 if all_classes_has_min_items_tagged(df, self.max_count) else self.max_count
        if all_images_tagged(df):
            print("All images are already tagged ...")
            self.write({'all_images_tagged': 1})
        else:
            next_class, next_image = resolve_image_name(df, max_count, _class)
            del df
            img_addr = "{}/{}/{}".format(self.images_url,
                                                        next_class,
                                                        next_image)
            print("Returning path: {}".format(img_addr))
            '''
            self.set_header('Content-Type', 'image/png')
            with open(img_addr, 'rb') as f:
                self.write(f.read())
            '''
            self.set_header('Access-Control-Allow-Origin', "*")
            self.write({"all_images_tagged": 0, "image_url": img_addr,
                        "class": next_class, "image_name": next_image})


class EnqueueAnnotationHandler(RequestHandler):

    def check_origin(self, origin):
        return True

    '''
    def initialize(self, queue):
        self.queue = queue
    '''

    def initialize(self, dataset_addr):
        self.dataset_addr = dataset_addr

    def get(self):
        _class = self.get_argument("class")
        image_name = self.get_argument("image_name")
        use_photo = self.get_argument("use_photo")
        d = pd.read_hdf(self.dataset_addr)
        print("Annotating Class: {}, Image name: {}, Use photo: {}".format(_class, image_name, use_photo))
        d.loc[(d['class'] == _class) & (d['image_name'] == image_name), 'use_photo'] = int(use_photo)
        d.to_hdf(self.dataset_addr, 'main')
        del d

        '''
        print("Enqueing. Class: {}, Image name: {}, Use photo: {}".format(_class, image_name, use_photo))
        self.queue.put({'class': _class, 'image_name': image_name, 'use_photo':
                      use_photo})
        '''

        self.set_header('Access-Control-Allow-Origin', "*")
        self.set_status(200)
        #return


def main(images_url, dataset_path, max_count=30):
    print("{} Starting Web Server ...".format(TAG))

    update_query_q = Queue()

    app = Application([
        (r"/get_photo", ProvidePhotoHandler,
         dict(dataset_addr=dataset_path,images_url=images_url,
                                                  max_count=max_count)),
        #(r"/save", EnqueueAnnotationHandler, dict(queue=update_query_q))
        (r"/save", EnqueueAnnotationHandler, dict(dataset_addr=dataset_path))
    ])

    '''
    update_worker_stopper = Event()
    Thread(target=dataset_update_worker, args=(dataset_path, update_query_q,
                                               update_worker_stopper)).start()
    '''

    app.listen(5000, '0.0.0.0')
    print("{} Server started ...".format(TAG))
    IOLoop.current().start()
    #update_worker_stopper.set()


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("images_url", help="URL of images")
    argp.add_argument("dataset_path", help="Path to dataset file")
    argp.add_argument("-m", "--max-images-perclass", help="A class has less priority if at least this parameter number of photos has been already tagged.", default=20, type=int)

    args = vars(argp.parse_args())

    main(args['images_url'], args['dataset_path'], args['max_images_perclass'])
