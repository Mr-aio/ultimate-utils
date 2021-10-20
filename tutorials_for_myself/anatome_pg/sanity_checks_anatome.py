#%%
"""
The similarity of the same network should always be 1.0 no matter what.
"""
import torch
import torch.nn as nn

import uutils.torch_uu
from uutils.torch_uu import cxa_sim, approx_equal
from uutils.torch_uu.models import get_named_identity_one_layer_linear_model

Din: int = 10
Dout: int = Din
B: int = 2000
mdl1: nn.Module = get_named_identity_one_layer_linear_model(D=Din)
mdl2: nn.Module = mdl1
layer_name = 'fc0'
# cxa_dist_type = 'pwcca'
cxa_dist_type = 'svcca'

X: torch.Tensor = torch.distributions.Normal(loc=0.0, scale=1.0).sample((B, Din))
sim: float = cxa_sim(mdl1, mdl2, X, layer_name, downsample_size=None, iters=1, cxa_dist_type=cxa_dist_type)

print(f'Should be very very close to 1.0: {sim=}')
print(f'Is it close to 1.0? {approx_equal(sim, 1.0)}')

#%%
"""
Make sure it returns sim 1.0 for linearly invertible linear net.
"""

# todo

#%%
"""
Reproducing: How many data points: https://github.com/google/svcca/blob/master/tutorials/001_Introduction.ipynb

As n increases, the cca sim should decrease until it converges to the true max linear correlation in the data.
This is because when D is small it's easy to correlate via Xw, Yw since there are less equations (m data) than unknown (D features). 
Similarly, the similarity decreases because the more data there is, the more variation has to be captured and thus the less
correlation there will be.
This is correct because 1/4*E[|| Xw - Yw||^2]^2 is proportional the pearson's correlation (assuming Xw, Yw is standardized).

"""
from pathlib import Path
from matplotlib import pyplot as plt

import torch
import torch.nn as nn

import uutils
from uutils.torch_uu import cxa_sim, approx_equal
from uutils.torch_uu.models import get_named_one_layer_random_linear_model

from uutils.plot import plot, save_to_desktop

B: int = 10  # [101, 200, 500, 1000, 2000, 5000, 10000]
Din: int = B
Dout: int = 100
mdl1: nn.Module = get_named_one_layer_random_linear_model(Din, Dout)
mdl2: nn.Module = get_named_one_layer_random_linear_model(Din, Dout)
layer_name = 'fc0'
# cxa_dist_type = 'pwcca'
cxa_dist_type = 'svcca'

X: torch.Tensor = uutils.torch_uu.get_identity_data(B)
sim: float = cxa_sim(mdl1, mdl2, X, layer_name, downsample_size=None, iters=1, cxa_dist_type=cxa_dist_type)

print(f'Should be very very close to 1.0: {sim=}')
print(f'Is it close to 1.0? {approx_equal(sim, 1.0)}')

# data_sizes: list[int] = [10, 25, 50, 100, 101, 200, 500, 1_000, 2_000, 5_000, 10_000, 50_000]
data_sizes: list[int] = [10, 25, 50, 100, 101, 200, 500, 1_000, 2_000, 5_000, 10_000]
sims: list[float] = []
for b in data_sizes:
    X: torch.Tensor = uutils.torch_uu.get_identity_data(b)
    mdl1: nn.Module = get_named_one_layer_random_linear_model(b, Dout)
    mdl2: nn.Module = get_named_one_layer_random_linear_model(b, Dout)
    sim: float = cxa_sim(mdl1, mdl2, X, layer_name, downsample_size=None, iters=1, cxa_dist_type=cxa_dist_type)
    sims.append(sim)

print(f'{sims=}')
plot(x=data_sizes, y=sims, xlabel='number of data points (n)', ylabel='similarity (svcca)', show=True, save_plot=True, plot_name='ndata_vs_svcca_sim')
