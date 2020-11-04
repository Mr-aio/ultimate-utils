"""
"""

from __future__ import division, print_function, absolute_import

import os
import re
import pdb
import glob
import pickle

import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import PIL.Image as PILI
import numpy as np

from pathlib import Path

from types import SimpleNamespace

from tqdm import tqdm

def get_support_query_batch_of_tasks_class_is_task_M_eq_N(args, SQ_x, SQ_y):
    """Get the Support & Query sets for a batch of tasks when tasks=classes and thus M=N.
    Split the data set of example {SQ_t}^N from the N tasks into it's Support set S and Query set Q.
    i.e. get S = {S_t}^N_t, Q = {Q_t}^N_t

    Args:
        args ([namespace]): experiment arguments.
        SQ_x ([torch([5, 20, 3, 84, 84])]): data examples from a batch of N task e.g. torch.Size([5, 20, 3, 84, 84])
        SQ_y ([torch.Size([5, 20])]): labels (task) for  a batch of N tasks e.g. torch.Size([5, 20])

    Returns:
        S_x {tensor([N,k_shot,C,H,W])} - Support set with k_shot image examples for each of the N classes. |S_x| = k_shot*N e.g. torch.Size([5,5, 3, 84, 84])
        S_y {tensor([N,k_shot])} - Support set with k_shot target examples for each of the N classes. |S_y| = k_shot*N e.g. torch.Size([5, 5])
        Q_x {tensor([N,k_eval,C,H,W])} - Query set with k_eval image examples for each of the N classes. |Q_x| = k_eval*N torch.Size([5, 15, 3, 84, 84])
        Q_y {tensor([N,k_eval])} - Query set with k_eval target examples for each of the N classes. |Q_x| = k_eval*N e.g. torch.Size([5, 15])
    """
    CHW = SQ_x.shape[-3:] # e.g. torch.Size([3, 84, 84])
    list_classes = range(args.n_classes) # classes=tasks here e.g. range(0, 5)
    ## Form Support data set S i.e. Sx = {Sx_t}^N_t & Sy = {Sy_t}^N_t, |Sx_t| = k_shot
    S_x = SQ_x[:, :args.k_shot, :, :, :].to(args.device) # e.g. torch.Size([5, 5, 3, 84, 84])
    # get labels for each of the k_shot examples for the N-way classes
    S_y = torch.stack([ torch.tensor([i]).repeat(args.k_shot) for i in list_classes ]).to(args.device) # e.g. torch.Size([5, 5])
    ## Form Query data set Q i.e. Qx = {Qx_t}^N_t & Qy = {Qy_t}^N_t, |Qx_t| = k_eval
    Q_x = SQ_x[:, args.k_shot:].to(args.device) # e.g. torch.Size([5, 15, 3, 84, 84])
    # get labels for each of the k_eval examples for the N-way classes
    Q_y = torch.stack([ torch.tensor([i]).repeat(args.k_eval) for i in list_classes ]).to(args.device) # e.g. torch.Size([5, 15])
    return S_x, S_y, Q_x, Q_y

def get_support_query_set_for_data_set_is_task(args, SQ_x, SQ_y):
    """In the meta-lstm paper they define task as a dataset. Thus, they sample a set of examples
    (k_eval+k_shot)*N and split those into a D^tr, D^test. 
    Note in this paper it's a subtle difference but a task is NOT a class. A task is a dataset.
    So the inner optimizer uses the whole D^tr when doing an adaptation rather than each class seperately.

    Args:
        args ([namespace]): experiment arguments.
        SQ_x ([torch([5, 20, 3, 84, 84])]): data examples from batch of task (k_shot+k_eval for each of the M tasks) e.g. torch.Size([5, 20, 3, 84, 84])
        SQ_y ([torch.Size([5, 20])]): labels (task) for  a batch of N tasks e.g. torch.Size([5, 20])

    Returns:
        S_x {tensor([k_shot*N,C,H,W])} - Support set with k_shot image examples for each of the N classes. |S_x| = k_shot*N e.g. torch.Size([25, 3, 84, 84])
        S_y {tensor([k_shot*N])} - Support set with k_shot target examples for each of the N classes. |S_y| = k_shot*N e.g. torch.Size([25])
        Q_x {tensor([k_eval*N,C,H,W])} - Query set with k_eval image examples for each of the N classes. |Q_x| = k_eval*N torch.Size([75, 3, 84, 84])
        Q_y {tensor([k_eval*N])} - Query set with k_eval target examples for each of the N classes. |Q_x| = k_eval*N e.g. torch.Size([75])
    """
    CHW = SQ_x.shape[-3:] # e.g. torch.Size([3, 84, 84])
    list_classes = range(args.n_classes) # e.g. range(0, 5)
    ## Form Support data set S i.e. Sx = {Sx_t}^M_t & Sy = {Sy_t}^M_t as a union (i.e. flatten tensor in the examples and classes dimension)
    # inner_inputs = SQ_x[:, :args.k_shot].reshape(-1, *episode_x.shape[-3:]).to(args.device) # [n_classes * k_shot, :]
    # inner_targets = torch.LongTensor(np.repeat(range(args.n_classes), args.k_shot)).to(args.device) # [n_classes * k_shot]
    S_x = SQ_x[:, :args.k_shot] # split to get the first 5 k_shot examples from each of the N labeled classes. e.g. torch.Size([5, 5, 3, 84, 84])
    # get labels for each of the k_shot examples for the N-way classes
    S_y = torch.LongTensor( np.repeat(list_classes, args.k_shot) ) # e.g. tensor([0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4])
    S_y = torch.LongTensor( S_y ).to(args.device) # [n_classes * k_shot] e.g. torch.Size([25])
    # to cuda
    S_x = S_x.to(args.device) # torch.Size([5, 5, 3, 84, 84])
    S_y = torch.LongTensor( S_y ).to(args.device) # tensor([0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4])
    ## Form Query data set Q i.e. Qx = {Qx_t}^M_t & Qy = {Qy_t}^M_t as a union (i.e. flatten tensor in the examples and classes dimension)
    # outer_inputs = episode_x[:, args.k_shot:].reshape(-1, *episode_x.shape[-3:]).to(args.device) # [n_classes * k_eval, :]
    # outer_targets = torch.LongTensor(np.repeat(range(args.n_classes), args.k_eval)).to(args.device) # [n_classes * k_eval]
    Q_x = SQ_x[:, args.k_shot:] # split to get the last 75 k_eval examples from each of the N labeled classes. e.g. torch.Size([5, 5*15, 3, 84, 84])
    # get labels for each of the k_eval examples for the N-way classes
    Q_y = np.repeat(list_classes, args.k_eval) # e.g. array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4])
    Q_y = torch.LongTensor( Q_y ).to(args.device) # [n_classes * k_eval] e.g. torch.Size([75])
    # to cuda
    Q_x = Q_x.to(args.device) # torch.Size([75, 3, 84, 84])
    Q_y = torch.LongTensor( Q_y ).to(args.device) # tensor([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4])
    #
    S_x = S_x.reshape(-1, *CHW) # [n_classes * k_shot, C, H, W] e.g. torch.Size([25, 3, 84, 84])
    Q_x = Q_x.reshape(-1, *CHW) # [n_classes * k_eval, C, H, W] e.g. torch.Size([75, 3, 84, 84])
    # to cuda
    S_x, S_y, Q_x, Q_y = S_x.to(args.device), S_y.to(args.device), Q_x.to(args.device), Q_y.to(args.device)
    return S_x, S_y, Q_x, Q_y

class MetaSet_Dataset(data.Dataset):
    """ A data set of data sets.
    Basically a list of "real" data sets e.g. { D_t }^64_t
    """

    def __init__(self, root, phase='train', k_shot=5, k_eval=15, transform=None):
        """Args:
            root (str): path to data
            phase (str): train, val or test
            k_shot (int): how many examples per class for training (k/n_support)
            k_eval (int): how many examples per class for evaluation
                - k_shot + k_eval = batch_size for data.DataLoader of ClassDataset
            transform (torchvision.transforms): data augmentation
        """
        ## Locate meta-set & tasl labels/idx i.e. get root to data-sets D_t for each task
        root = os.path.join(root, phase) # e.g '/Users/brandomiranda/automl-meta-learning/data/miniImagenet/train'
        # count the number of classes
        self.labels = sorted(os.listdir(root)) # e.g. 64 for meta-train, 16 for meta-val, 20 for meta-test
        
        ## Get meta-set
        meta_set_as_paths = [] # e.g. holds all the paths to the images e.g. 64 tasks/classes of mini-imagenet
        for label in self.labels: # for each label get the 600 paths to the images
            ## Append path to Dt to meta_set
            # get e. path to D_t with 600
            path_to_Dt = os.path.join(root, label, '*') # e.g. '/Users/brandomiranda/automl-meta-learning/data/miniImagenet/train/n13133613/*' note * is to match all names of images
            # get path to all (600) images to current images of D_t. Note: glog.glob = Return a possibly-empty list of path names that match pathname, since at the end we have * we match all images.
            list_pathnames_of_images = glob.glob( path_to_Dt ) # e.g. ['/Users/brandomirand...00181.jpg', '/Users/brandomirand...00618.jpg', '/Users/brandomirand...00624.jpg', '/Users/brandomirand...00630.jpg', '/Users/brandomirand...00397.jpg', '/Users/brandomirand...01089.jpg', '/Users/brandomirand...00368.jpg', '/Users/brandomirand...00340.jpg', '/Users/brandomirand...00432.jpg', '/Users/brandomirand...00591.jpg', '/Users/brandomirand...01102.jpg', '/Users/brandomirand...00234.jpg', '/Users/brandomirand...00220.jpg', '/Users/brandomirand...00546.jpg', ...]
            meta_set_as_paths.append( path_to_Dt ) # append list of 600 paths to images for Dt
        # returns meta_set_as_paths = [Path_Dt]^64_t=1 where |D_t| = 600

        ## Generate list of dataloaders for each Class-data set of size 600. With the dataloader for each class Dataset we can sample a N-way K-shot task of size N*K
        self.episode_loader = []
        for idx, _ in enumerate(self.labels):
            ##
            # wrap each task D_t in a class Dataset
            label = idx # get class/label for current task e.g. out of 64 tasks idx \in [0,...,63]
            path_to_task_imgs = meta_set_as_paths[idx] # list for 600 images for the current task
            Dt_classdataset = ClassDataset(images=path_to_task_imgs, label=label, transform=transform) # task D_t
            # 
            nb_examples_for_S_Q = k_shot+k_eval
            Dt_class_loader = data.DataLoader(Dt_classdataset, batch_size=nb_examples_for_S_Q, shuffle=True, num_workers=0) # data loader for the current task D_t for class/label t
            self.episode_loader.append(Dt_class_loader) # collect all tasks so this is size e.g. 64 or 16 or 20 for each meta-set
        print(f'len(self.episode_loader) = {len(self.episode_loader)}') # e.g. this list is of size 64 for meta-train-set (or 16, 20 meta-val, meta-test)

    def __getitem__(self, idx):
        """Get a batch of examples k_shot+k_eval from a single task D_t ~~ p(x,y|t) to be split into the suppport and query set S_t, Q_t.

        Args:
            idx ([int]): index for the task (class label) e.g. idx in range [1 to 64]

        Returns:
            [TODO]: returns the tensor of all examples k_shot+k_eval to be split into S_t and Q_t fur current task=idx e.g. size [20, C,H,W] if k_shot+k_eval=20
        """
        # return next(iter(self.episode_loader[idx]))
        ## get dataloader for task D_t
        label = idx # task label e.g. single tensor(22)
        Dt_task_dataloader = iter(self.episode_loader[label]) # dataloader class that samples examples form task, mimics x,y ~ P(x,y|task=idx), tasks are modeled by index/label in this problem
        # get current data set D = (D^{train},D^{test}) as a [k_shot, c, h, w] tensor
        ## Sample k_eval examples to form the query and support set e.g. sample batch of size 20 images from 600 available in the current task to later form S_t,Q_t
        SQ_x,S_y = next(Dt_task_dataloader) # e.g. 20=k_shot+k_eval images and intergers representing the label e.g. (tensor([[[[-0.0801, ....2641]]]]), tensor([22, 22, 22, ...  22, 22]))
        return [SQ_x,S_y] # e.g. tuples of 20 x's and y's for task t/label. All y=t. e.g. (tensor([[[[-0.0801, ....2641]]]]), tensor([22, 22, 22, ...  22, 22]))

    def __len__(self):
        """ Returns the number of tasks D_t.

        Returns:
            [int]: number of tasks e.g. 64 for mini-Imagenet's meta-train-set
        """
        return len(self.labels) # e.g. 64 for mini-Imagenet's meta-train-set 

class ClassDataset(data.Dataset):

    def __init__(self, images, label, transform=None):
        """Args:
            images (list of str): each item is a path to an image of the same label
            label (int): the label of all the images
        """
        self.images = images # e.g. ['/Users/brandomirand...00106.jpg', '/Users/brandomirand...01218.jpg', '/Users/brandomirand...00660.jpg', '/Users/brandomirand...00674.jpg', '/Users/brandomirand...00884.jpg', '/Users/brandomirand...00890.jpg', '/Users/brandomirand...00648.jpg', '/Users/brandomirand...01230.jpg', '/Users/brandomirand...00338.jpg', '/Users/brandomirand...00489.jpg', '/Users/brandomirand...00270.jpg', '/Users/brandomirand...00264.jpg', '/Users/brandomirand...01152.jpg', '/Users/brandomirand...00258.jpg', ...]
        self.label = label # e.g. 37
        self.transform = transform

    def __getitem__(self, idx):
        """
        Args:
            idx ([int]): an index from D_t e.g. 261

        Returns:
            [tensor, int]: single example (x,y) where y is an int.
        """
        ## get a single image (and transform it if necessary)
        image = PILI.open(self.images[idx]).convert('RGB')
        if self.transform is not None:
            image = self.transform(image)
        return image, self.label 

    def __len__(self):
        """ 
        Returns:
            [int]: number of images x in D_t
        """
        return len(self.images) # e.g. 600

class EpisodicSampler(data.Sampler):
    """

    Comments:
        Meant to be passed to batch_sampler when creating a data_loader.
        batch_sampler = A custom Sampler that yields a list of batch indices at a time can be passed as the batch_sampler argument.
    """

    def __init__(self, total_classes, n_classes, n_episode):
        """[summary]

        Args:
            total_classes ([int]): total number of tasks for a meta-set e.g. 64, 16, 20 for mini-imagenet
            n_classes ([int]): the number of classes to sample e.g. 5
            n_episode ([int]): [description]
        """
        self.total_classes = total_classes # e.g. 64, 16, 20 for mini-imagenet (total number of tasks for a meta-set)
        self.n_classes = n_classes # the number of classes to sample e.g. 5
        self.n_episode = n_episode # number of times to samples from a task D_t e,g, 60K for MAML/meta-lstm.

    def __iter__(self):
        """Returns/yields a batch of indices representing the batch of tasks.

        Yields:
            [list of ints]: yields a batch of tasks (class indicies) represented as a list of integers in the range(0,N_meta-set). Usually of size N e.g. 5 for 5-way.
        """
        for episode in range(self.n_episode):
            # Sample a random permutation of indices for all tasks/classes e.g. random permutation of nat's from 0 to 63
            random_for_indices_all_tasks = torch.randperm(self.total_classes) # Return a random permutation of integers in a range e.g. tensor([28, 36, 53, 6, 2, 38, 9, 42, 46, 58, 44, 25, 41, 20, 26, 62, 57, 63, 16, 27, 32, 61, 29, 21, 45, 48, 60, 7, 56, 0, 47, 4, 50, 39, 49, 35, 43, 15, 33, 17, 13, 24, 59, 14, 22, 37, 34, 1, 8, 11, 10, 54, 3, 51, 19, 52, 12, 5, 31, 23, 55, 18, 30, 40])
            # Sample a batch of tasks. i.e. select self.n_classes (e.g. 5) task indices.
            indices_batch_tasks = random_for_indices_all_tasks[:self.n_classes] # e.g. tensor([28, 45, 31, 29,  7])
            # stateful return, when iterator is called it continues executing the next line using the state from the last place it was left off, in this case the main state being remembered is the # of episodes. So this generator ends once the # of episodes has been reached.
            yield indices_batch_tasks

    def __len__(self):
        """Returns the number of episodes.

        Returns:
            [int]: returns the number of times we will sample episodes
        """
        return self.n_episode

def prepare_data_for_few_shot_learning(args):
    """[summary]

    Args:
        args ([type]): [description]

    Returns:
        [DataLoader]: metatrainset_loader; a dataloader that samples the data for a batch of tasks. 
            e.g. a sample of it produces 
        [DataLoader]: metavalset_loader.
        [DataLoader]: metatestset_loader.
    """
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ## Get the meta-sets as dataset classes.
    metatrainset = MetaSet_Dataset(args.data_root, 'train', args.k_shot, args.k_eval,
        transform=transforms.Compose([
            transforms.RandomResizedCrop(args.image_size),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(
                brightness=0.4,
                contrast=0.4,
                saturation=0.4,
                hue=0.2),
            transforms.ToTensor(),
            normalize])
            )
    metavalset = MetaSet_Dataset(args.data_root, 'val', args.k_shot, args.k_eval,
        transform=transforms.Compose([
            transforms.Resize(args.image_size * 8 // 7),
            transforms.CenterCrop(args.image_size),
            transforms.ToTensor(),
            normalize])
            )
    metatestset = MetaSet_Dataset(args.data_root, 'test', args.k_shot, args.k_eval,
        transform=transforms.Compose([
            transforms.Resize(args.image_size * 8 // 7),
            transforms.CenterCrop(args.image_size),
            transforms.ToTensor(),
            normalize])
            )
    ## Get episodic samplers. They sampler task (indices) according to args.n_classes for args.episodes episodes. e.g. samples 5 tasks (idx) for 60K episodes.
    episode_sampler_metatrainset = EpisodicSampler(len(metatrainset), args.n_classes, args.episodes)
    episode_sampler_metavalset = EpisodicSampler(len(metavalset), args.n_classes, args.episodes_val)
    episode_sampler_metatestset = EpisodicSampler(len(metatestset), args.n_classes, args.episodes_test)
    ## Get the loaders for the meta-sets. These return the sample of tasks used for meta-training.
    metatrainset_loader = data.DataLoader(metatrainset, num_workers=args.n_workers, pin_memory=args.pin_mem, batch_sampler=episode_sampler_metatrainset)
    metavalset_loader = data.DataLoader(metavalset, num_workers=4, pin_memory=False, batch_sampler=episode_sampler_metavalset)
    metatestset_loader = data.DataLoader(metatestset, num_workers=4, pin_memory=False, batch_sampler=episode_sampler_metatestset)
    return metatrainset_loader, metavalset_loader, metatestset_loader

def get_args_for_mini_imagenet():
    from automl.child_models.learner_from_opt_as_few_shot_paper import Learner

    args = SimpleNamespace()
    #
    args.n_workers = 4
    args.pin_mem = True #TODO what is this?
    #
    args.k_shot = 5
    args.k_eval = 15
    args.n_classes = 5 # M, # of tasks to sample. Note N=M, N from N way
    args.episodes = 5
    args.episodes_val = 4
    args.episodes_test = 3
    args.image_size = 84
    args.data_root = Path("~/automl-meta-learning/data/miniImagenet").expanduser()
    args.S_batch_size = 25 # batch size for the union of tasks in the support set. Must be <= k_shot*M or <= k_shot*N
    #
    args.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    args.nb_inner_train_steps = 3
    #
    args.bn_momentum = 0.95
    args.bn_eps = 1e-3
    args.base_model = Learner(args.image_size, args.bn_eps, args.bn_momentum, args.n_classes)
    #
    args.criterion = nn.CrossEntropyLoss()
    return args

def test_episodic_loader_inner_loop_per_task_good_accumulator(debug_test=True):
    import automl.child_models.learner_from_opt_as_few_shot_paper as learner_from_opt_as_few_shot_paper
    import higher
    
    ## get args for test
    args = get_args_for_mini_imagenet()
    ## get base model that meta-lstm/maml use
    base_model = learner_from_opt_as_few_shot_paper.Learner(image_size=args.image_size, bn_eps=args.bn_eps, bn_momentum=args.bn_momentum, n_classes=args.n_classes).to(args.device)
    ## get meta-sets
    metatrainset_loader, metavalset_loader, metatestset_loader = prepare_data_for_few_shot_learning(args)
    ## start episodic training
    meta_params = base_model.parameters()
    outer_opt = optim.Adam(meta_params, lr=1e-2)
    base_model.train()
    for episode, (SQ_x, SQ_y) in enumerate(metatrainset_loader):
        S_x, S_y, Q_x, Q_y = get_support_query_batch_of_tasks_class_is_task_M_eq_N(args, SQ_x, SQ_y)
        ## Get Inner Optimizer (for maml)
        inner_opt = torch.optim.SGD(base_model.parameters(), lr=1e-1)
        nb_tasks = S_x.size(0) 
        with higher.innerloop_ctx(base_model, inner_opt, copy_initial_weights=False, track_higher_grads=False) as (fmodel, diffopt):
            meta_losses = [] 
            for t in range(nb_tasks):
                Sx_t, Sy_t, Qx_t, Qy_t = S_x[t,:,:,:], S_y[t,:], Q_x[t,:,:,:], Q_y[t,:]
                for i_inner in range(args.nb_inner_train_steps): # this current version implements full gradient descent on k_shot examples (which is usually small  5)
                    fmodel.train()
                    # base/child model forward pass
                    S_logits_t = fmodel(Sx_t) 
                    inner_loss = args.criterion(S_logits_t, Sy_t)
                    # inner-opt update
                    diffopt.step(inner_loss)
                ## Evaluate on query set for current task
                qrt_logits_t = fmodel(Qx_t)
                qrt_loss_t = args.criterion(qrt_logits_t, Qy_t)
                meta_losses.append(qrt_loss_t.detach()) # remove history so it be memory efficient and able to print stats
                ## Update the model's meta-parameters to optimize the query losses across all of the tasks sampled in this batch. This unrolls through the gradient steps.
                qrt_loss_t.backward() # this also accumualtes the gradients wrt to query loss more memory efficiently as it removes history that is not needed anymore
        print(f'[episode={episode}] base_model.model.features.conv1.weight.grad = {base_model.model.features.conv1.weight.grad}')
        outer_opt.step()
        outer_opt.zero_grad()
        print(f'[episode={episode}] meta_loss = {sum(meta_losses)}')

if __name__ == "__main__":
    test_episodic_loader_inner_loop_per_task_good_accumulator()