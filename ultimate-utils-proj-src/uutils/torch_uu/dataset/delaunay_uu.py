"""

The final dataset comprises 11, 503 samples across 53
classes, i.e., artists (mean number of samples per artist: 217.04;
standard deviation: 58.55), along with their source URLs.

These samples are split between a training set of 9202 images, and a test set of 2301 images.

Due to the heterogeneous nature
of sources, images vary significantly in their resolution, from
80px × 80px for the smallest sample to 3365px × 4299px for
the largest.

ref:
- https://arxiv.org/abs/2201.12123
- data set to learn2learn task set: https://github.com/learnables/learn2learn/issues/375
"""
import torch
from datetime import datetime

from argparse import Namespace

import os
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from torchvision.datasets import ImageFolder
from torchvision.transforms import transforms, Compose, ToPILImage, RandomCrop, ColorJitter, RandomHorizontalFlip, \
    ToTensor

from typing import Union

from pathlib import Path

from uutils import download_and_extract, expanduser, move_folders_recursively

mean = [0.5853, 0.5335, 0.4950]
std = [0.2348, 0.2260, 0.2242]
normalize = transforms.Normalize(mean=mean,
                                 std=std)

classes = ('Ad Reinhardt', 'Alberto Magnelli', 'Alfred Manessier', 'Anthony Caro',
           'Antoine Pevsner', 'Auguste Herbin', 'Aurélie Nemours', 'Berto Lardera',
           'Charles Lapicque', 'Charmion Von Wiegand', 'César Domela', 'Ellsworth Kelly',
           'Emilio Vedova', 'Fernand Léger', 'František Kupka', 'Franz Kline',
           'François Morellet', 'Georges Mathieu', 'Georges Vantongerloo',
           'Gustave Singier', 'Hans Hartung', 'Jean Arp', 'Jean Bazaine', 'Jean Degottex',
           'Jean Dubuffet', 'Jean Fautrier', 'Jean Gorin', 'Joan Mitchell',
           'Josef Albers', 'Kenneth Noland', 'Leon Polk Smith', 'Lucio Fontana',
           'László Moholy-Nagy', 'Léon Gischia', 'Maria Helena Vieira da Silva',
           'Mark Rothko', 'Morris Louis', 'Naum Gabo', 'Olle Bærtling', 'Otto Freundlich',
           'Pierre Soulages', 'Pierre Tal Coat', 'Piet Mondrian', 'Richard Paul Lohse',
           'Roger Bissière', 'Sam Francis', 'Sonia and Robert Delaunay', 'Sophie Taeuber-Arp',
           'Theo van Doesburg', 'Vassily Kandinsky', 'Victor Vasarely', 'Yves Klein', 'Étienne Béothy')


def download_delauny_original_data(extract_to: Path = Path('~/data/delauny_original_data/'),
                                   path_2_zip=Path('~/data/delauny_original_data/'),
                                   url_all: str = 'https://physiologie.unibe.ch/supplementals/delaunay.zip',
                                   url_train: str = 'https://physiologie.unibe.ch/supplementals/delaunay_train.zip',
                                   url_test: str = 'https://physiologie.unibe.ch/supplementals/delaunay_test.zip',
                                   url_img_urls: str = 'https://physiologie.unibe.ch/supplementals/DELAUNAY_URLs.zip',
                                   ):
    """
    Downloads the abstract art delauny data set for ML and other research.

python -u ~/ultimate-utils/ultimate-utils-proj-src/uutils/torch_uu/dataset/delaunay_uu.py
nohup python -u ~/ultimate-utils/ultimate-utils-proj-src/uutils/torch_uu/dataset/delaunay_uu.py > delauny.out &

    ref: https://github.com/camillegontier/DELAUNAY_dataset/issues/2
    """
    extract_to: Path = expanduser(extract_to)
    download_and_extract(url_all, path_used_for_zip=path_2_zip, path_used_for_dataset=extract_to)
    download_and_extract(url_train, path_used_for_zip=path_2_zip, path_used_for_dataset=extract_to)
    download_and_extract(url_test, path_used_for_zip=path_2_zip, path_used_for_dataset=extract_to)
    download_and_extract(url_img_urls, path_used_for_zip=path_2_zip, path_used_for_dataset=extract_to)

    # urls = [url_all, url_train, url_test, url_img_urls]
    # # - download data (could be made faster with mp or asyncio, whatever)
    # for url in urls:
    #     download_and_unzip(url, extract_to)


def process_delanauny_into_pickle_files():
    """not going to do it for now, just keep the folder per image setup. Effortless. Unless it becomes a problem."""
    pass
    # NOP


def get_min_max_size_of_images_delany() -> tuple[int, int]:
    """
    Loop through data sets (all images) and collect the min and max sizes. Also print the channels, assert it to be 3.

    ref:
        - ask for recommended size form original authors https://github.com/camillegontier/DELAUNAY_dataset/issues/4
        decided to stick with 84 since looping through it worked without issues.
    """
    print('decided not to print it since the current data transform went through all the images without issues')


def get_data_augmentation():
    pass  # todo


def _original_data_transforms_delauny(size: int = 256) -> transforms.Compose:
    transform = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean,
                             std=std),
    ])
    return transform


def get_my_delauny_data_transforms(data_augmentation: str = 'delauny_uu',
                                   size: int = 84,
                                   ) -> tuple[Compose, Compose, Compose]:
    """

    Notes:
        - RandomCrop has padding = 8 because this likely makes it more robust against images with surrounding contours/padding.
        - val transform == test transform because: I agree to use test transforms on validation. It reduces the variance on the validation and since your not fitting them anyway there is likely little benefit to early stop with complicated train data augmentation for valitation. Better to have a low variance estimate of an unknown distribution so to early stop more precisely.

    ref:
        - https://github.com/learnables/learn2learn/issues/309
        - padding for random crop discussion: https://datascience.stackexchange.com/questions/116201/when-to-use-padding-when-randomly-cropping-images-in-deep-learning
    """
    print(f'{size=} for my delauny.')
    if data_augmentation is None:
        raise NotImplementedError
        # return original delauny transforms
    elif data_augmentation == 'delauny_uu':
        # is it ok to do ToTransform (and normalize) before other data gumentation techniques? https://stackoverflow.com/questions/74451955/is-it-safe-to-do-a-totensor-data-transform-before-a-colorjitter-and-randomhori
        train_data_transform = Compose([
            # ToPILImage(),
            RandomCrop(size, padding=8),
            # decided 8 due to https://datascience.stackexchange.com/questions/116201/when-to-use-padding-when-randomly-cropping-images-in-deep-learning
            ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4),
            RandomHorizontalFlip(),
            ToTensor(),
            normalize,
        ])
        test_data_transform = transforms.Compose([
            transforms.Resize((size, size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean,
                                 std=std),
        ])
        validation_data_transform = test_data_transform
    else:
        raise ValueError(f'Err: {data_augmentation=}')
    return train_data_transform, validation_data_transform, test_data_transform


def get_delauny_dataset_splits(path2train: str,
                               path2val: str,
                               path2test: str,
                               data_augmentation: str = 'delauny_uu',
                               size: int = 84,
                               random_split: bool = False,
                               ) -> tuple[Dataset, Dataset, Dataset]:
    """ """
    # - expand paths
    path2train: Path = expanduser(path2train)
    path2val: Path = expanduser(path2val)
    path2test: Path = expanduser(path2test)
    # - data transforms
    train_data_transform, validation_data_transform, test_data_transform = get_my_delauny_data_transforms(
        data_augmentation, size)
    # -
    train_dataset = ImageFolder(path2train, transform=train_data_transform)
    if random_split:
        print(f'printing path2val since your using random split, make sure its the empty string: {str(path2val)=}')
        train_dataset, valid_dataset = torch.utils.data.random_split(train_dataset,
                                                                     [7362, 1840],
                                                                     generator=torch.Generator().manual_seed(42))
        assert str(path2val) != '', f'Err: you have a path2val but we are randomly splitting: {path2val=}'
    else:
        valid_dataset = ImageFolder(path2val, transform=validation_data_transform)
    test_dataset = ImageFolder(path2test, transform=test_data_transform)
    return train_dataset, valid_dataset, test_dataset


def create_your_splits(path_to_all_data: Union[str, Path],
                       path_for_splits: Union[str, Path],
                       ):
    """
    Details on my Delauny few-shot learning data set splits:
    - 34, 8, 11
    - split is deterministic (and arbitrary) based on sorting -- to guarantee determinisim. Hopefully this is diverse enough,
    the diversity for this arbitrary split is: mu +- ci.
    - make sure .labels is set i.e. the 34, 8, 11 & asserts there.
    """
    # - get path to union of all images & sort based on alphabetical path to folder [likely first name] (might be useful for usl!)
    path_to_all_data: Path = expanduser(path_to_all_data)
    dirpath, dirnames, filenames = next(iter(os.walk(path_to_all_data)))
    print(f'{dirpath=}, {path_to_all_data=}')
    # assert dirpath == path_to_all_data
    assert len(dirnames) == 53
    # - split into 34, 8, 11 splits (based on previous sorting list)
    sorted_dirnames: list = list(sorted(dirnames))
    train_val = sorted_dirnames[:42]
    train = train_val[:34]
    val = train_val[34:]
    test = sorted_dirnames[42:]
    assert len(train) == 34
    assert len(val) == 8
    assert len(test) == 11
    # - save the few-shot learning 34, 8, 11 splits as folders with images (based on previous sorting list)
    path_for_splits: Path = expanduser(path_for_splits)
    path2train: Path = path_for_splits / 'delauny_train_split_dir'
    move_folders_recursively(root=path_for_splits / 'delauny_train_split_dir', dirnames=train)
    path2val: Path = path_for_splits / 'delauny_validation_split_dir'
    move_folders_recursively(root=path_for_splits / 'delauny_validation_split_dir', dirnames=val)
    path2test: Path = path_for_splits / 'delauny_test_split_dir'
    move_folders_recursively(root=path_for_splits / 'delauny_test_split_dir', dirnames=test)
    # - print the paths to the 3 splits. Check them manually (or print ls to them and print the lst)
    print(f'{path2train=}')
    print(f'{path2val=}')
    print(f'{path2test=}')
    # - later, compute the task2vec div of the train 34 and test 11 splits.
    # args: Namespace = load_args()
    # args: Namespace = Namespace()
    # args: Namespace = diversity_ala_task2vec_delauny_resnet18_pretrained_imagenet()
    # compute_div_and_plot_distance_matrix_for_fsl_benchmark(args, show_plots=False)
    # ## compute_div_and_plot_distance_matrix_for_fsl_benchmark(args)


# - tests

def diversity_ala_task2vec_delauny_resnet18_pretrained_imagenet(args: Namespace) -> Namespace:
    # args.batch_size = 500
    args.batch_size = 2
    args.data_option = 'delauny'  # no name assumes l2l, make sure you're calling get_l2l_tasksets
    args.data_path = Path('~/data/l2l_data/').expanduser()
    args.data_augmentation = 'delauny'

    # - probe_network
    args.model_option = 'resnet18_pretrained_imagenet'

    # -- wandb args
    args.wandb_project = 'entire-diversity-spectrum'
    # - wandb expt args
    current_time = datetime.now().strftime('%b%d_%H-%M-%S')
    args.experiment_name = f'diversity_ala_task2vec_mi_resnet18'
    args.run_name = f'{args.experiment_name} {args.batch_size=} {args.data_option} {args.model_option} {current_time}'
    # args.log_to_wandb = True
    args.log_to_wandb = False

    from uutils.argparse_uu.meta_learning import fix_for_backwards_compatibility
    args = fix_for_backwards_compatibility(args)
    return args


def loop_raw_pytorch_delauny_dataset_with_my_data_transforms_and_print_min_max_size():
    path2train: str = '~/data/delauny_original_data/DELAUNAY_train'
    path2val: str = ''
    path2test: str = '/Users/brandomiranda/data/delauny_original_data/DELAUNAY_test'
    random_split = True
    train_dataset, valid_dataset, test_dataset = get_delauny_dataset_splits(path2train, path2val, path2test,
                                                                            random_split=random_split)
    train_loader: DataLoader = DataLoader(train_dataset, num_workers=1)
    valid_loader: DataLoader = DataLoader(valid_dataset, num_workers=1)
    test_loader: DataLoader = DataLoader(test_dataset, num_workers=1)
    next(iter(train_loader))
    next(iter(valid_loader))
    next(iter(test_loader))
    # -
    concat = ConcatDataset([train_dataset, valid_dataset, test_dataset])
    assert len(concat) == len(train_dataset) + len(valid_dataset) + len(test_dataset)
    for i, (x, _) in enumerate(concat):
        print(f'{x=}')
        print(f'{x.size()=}')
        # size = x.size()
        break
    # - print min & max sizes
    print('decided not to print it since the current data transform went through all the images without issues')


if __name__ == "__main__":
    import time
    from uutils import report_times

    start = time.time()
    # - run experiment
    # download_delauny_original_data()
    loop_raw_pytorch_delauny_dataset_with_my_data_transforms_and_print_min_max_size()
    # - Done
    print(f"\nSuccess Done!: {report_times(start)}\a")
