import pandas as pd

def annotations_counts(d):
    ret = {}
    ret['total_classes'] = d['class'].unique().shape[0]
    ret['total_photos'] = d.shape[0]
    d = d[d.use_photo != -1]
    ret['total_photos_annotated'] = d.shape[0]
    ret['total_classes_annotated'] = d['class'].unique().shape[0]
    ret['total_usable_photos'] = d[d.use_photo == 1].shape[0]
    ret['total_not_usable_photos'] = ret['total_photos_annotated'] - ret['total_usable_photos']
    ret['total_mean_photos_by_class'] = ret['total_photos_annotated']/ ret['total_classes_annotated']
    ret['total_usable_classes'] = d.loc[d.use_photo == 1, 'class'].unique().shape[0]
    ret['mean_usable_photo_by_class'] = ret['total_usable_photos'] / ret['total_usable_classes']
    return ret


def metrics(data_addr):
    d = pd.read_hdf(data_addr)
    ann_insts = d[d.instant > 0]
    insts = ann_insts.instant.values
    insts.sort()
    pass
