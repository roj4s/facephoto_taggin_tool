import argparse
from queue import Queue
import pandas as pd
from threading import Thread
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop

TAG = "[TagginToolWebServer]"
update_query_q = Queue()

def dataset_update_worker(dataset_addr, stop_event):
    tag = '[UpdateWorker]'
    d = pd.read_hdf(dataset_addr)
    while not stop_event.is_set():
        query = update_query_q.get()
        print("{} Got new query. Class: {}, Image {}, Use: {}".format(tag,
                                                                      query['class'],
                                                                     query['image_name'],
                                                                     query['use_photo']))
        d[(d['class'] == query['class']) & (d['image_name'] == query['image_name'])]['use_photo'] = query['use_photo']
        d.to_hdf(dataset_addr)

def resolve_image_name(df, max_count, starting_class=None):
    while True:
        if starting_class is None:
            starting_class = df[df.use_photo == -1].sample(1)['class'].iloc[0]

        not_tagged_yet = df[(df['class'] == starting_class) & (df['use_photo']
                                                              == -1)]
        if not_tagged_yet.empty:
            starting_class = None
            continue

        tagged_already = df[(df['class'] == starting_class) & (df['use_photo']
                                                              != -1)]

        if max_count != -1 and tagged_already.count()[0] >= max_count:
            starting_class = None
            continue

        return not_tagged_yet.sample(1)[['class', 'image_name']].values[0]

def all_images_tagged(df):
    return not df[df.use_photo != -1].empty

def all_classes_has_min_items_tagged(df, count):
    tagged_by_class = df[df.use_photo != -1].groupby('class')
    return tagged_by_class.filter(lambda x: len(x) < count).empty

class ProvidePhotoHandler(RequestHandler):

    def initialize(self, dataset_addr, images_url, max_count=30):
        self.df = pd.read_hdf(dataset_addr)
        self.max_count = -1 if all_classes_has_min_items_tagged(self.df,
                                                                max_count) else max_count
        self.images_url = images_url

    def get(self):
        _class = self.get_body_argument("class", None)

        if all_images_tagged(self.df):
            self.write({'all_images_tagged': 1})
        else:
            next_class, next_image = resolve_image_name(self.df, self.max_count, _class)
            self.write({'image_path': "{}/{}/{}".format(self.images_url,
                                                        next_class,
                                                        next_image),
                        'all_images_tagged': 0})


def main(images_url, dataset_path, max_count=30):
    print("{} Starting Web Server ...".format(TAG))
    app = Application([
        (r"/get_photo", ProvidePhotoHandler,
         dict(dataset_addr=dataset_path,images_url=images_url,
                                                  max_count=max_count)),
    ])

    app.listen(5000, '0.0.0.0')
    print("{} Server started ...".format(TAG))
    IOLoop.current().start()


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("images_url", help="URL of images")
    argp.add_argument("dataset_path", help="Path to dataset file")
    argp.add_argument("-m", "--max-images-perclass", help="A class has less priority if at least this parameter number of photos has been already tagged.", default=20, type=int)

    args = vars(argp.parse_args())

    main(args['images_url'], args['dataset_path'], args['max_images_perclass'])
