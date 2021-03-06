import os
from itertools import repeat
import ctypes

import numpy as np
import numpy.testing as npt
import nose.tools as nt
from scipy.integrate import simps

import popeye.utilities as utils
from popeye import spatiotemporal_hrf as strf
from popeye.visual_stimulus import VisualStimulus, simulate_bar_stimulus, resample_stimulus

def test_strf_hrf_fit():
    
    viewing_distance = 38
    screen_width = 25
    thetas = np.tile(np.arange(0,360,90),2)
    thetas = np.insert(thetas,0,-1)
    thetas = np.append(thetas,-1)
    num_blank_steps = 20
    num_bar_steps = 20
    ecc = 10
    tr_length = 1.0
    frames_per_tr = 1.0
    scale_factor = 0.50
    pixels_down = 200
    pixels_across = 200
    dtype = ctypes.c_int16
    Ns = 3
    voxel_index = (1,2,3)
    auto_fit = True
    verbose = 1
    projector_hz = 480
    tau = 0.00875
    mask_size = 5
    
    # create the sweeping bar stimulus in memory
    stim = simulate_bar_stimulus(pixels_across, pixels_down, viewing_distance, 
                                 screen_width, thetas, num_bar_steps, num_blank_steps, ecc)
    
    # create an instance of the Stimulus class
    stimulus = VisualStimulus(stim, viewing_distance, screen_width, scale_factor, tr_length, dtype)
    stimulus.fps = projector_hz
    flicker_vec = np.zeros_like(stim[0,0,:]).astype('uint8')
    flicker_vec[1*20:5*20] = 1
    flicker_vec[5*20:9*20] = 2
    stimulus.flicker_vec = flicker_vec
    stimulus.flicker_hz = [10,20]
    
    # initialize the gaussian model
    model = strf.SpatioTemporalModel(stimulus, utils.double_gamma_hrf)
    model.tau = tau
    model.mask_size = mask_size
    
    # generate a random pRF estimate
    x = -2.24
    y = 1.58
    sigma = 1.23
    weight = 0.90
    hrf_delay = -0.13
    beta = 1.0
    baseline = -0.25
    
    # create the "data"
    data =  model.generate_prediction(x, y, sigma, weight, hrf_delay, beta, baseline)
    
    # set search grid
    x_grid = utils.grid_slice(-8.0,7.0,3)
    y_grid = utils.grid_slice(-8.0,7.0,3)
    s_grid = utils.grid_slice(0.75,3.0,3)
    w_grid = utils.grid_slice(0.05,0.95,3)
    h_grid = utils.grid_slice(-0.25,0.25,3)
    
    # set search bounds
    x_bound = (-10,10)
    y_bound =  (-10,10)
    s_bound = (1/stimulus.ppd,10)
    w_bound = (1e-8,1.0)
    b_bound = (1e-8,1e5)
    u_bound = (None, None)
    h_bound = (-2.0,2.0)
    
    # loop over each voxel and set up a GaussianFit object
    grids = (x_grid, y_grid, s_grid, w_grid, h_grid,)
    bounds = (x_bound, y_bound, s_bound, w_bound, h_bound, b_bound, u_bound)
    
    # fit the response
    fit = strf.SpatioTemporalFit(model, data, grids, bounds)
    
    # coarse fit
    npt.assert_almost_equal((fit.x0,fit.y0,fit.sigma0,fit.weight0,fit.hrf0,fit.beta0,fit.baseline0),[-0.5 , -0.5 ,  3.  ,  0.95, -0.25,  1.  ,  0.02], 2)
    
    # fine fit
    npt.assert_almost_equal(fit.x, x, 2)
    npt.assert_almost_equal(fit.y, y, 2)
    npt.assert_almost_equal(fit.sigma, sigma, 2)
    npt.assert_almost_equal(fit.weight, weight, 2)
    npt.assert_almost_equal(fit.beta, beta, 2)
    npt.assert_almost_equal(fit.baseline, baseline, 2)
    
    # overloaded
    npt.assert_almost_equal(fit.overloaded_estimate, [ 2.53,  2.74,  1.23,  0.9 ,  5.87,  1.  , -0.25],2)
                                                      
    m_rf = fit.model.m_rf(fit.model.tau)
    p_rf = fit.model.p_rf(fit.model.tau)
    npt.assert_almost_equal(simps(np.abs(m_rf)),simps(p_rf),5)
    
    # responses
    m_resp = fit.model.generate_m_resp(fit.model.tau)
    p_resp = fit.model.generate_p_resp(fit.model.tau)
    npt.assert_(np.max(m_resp,0)[0]<np.max(m_resp,0)[1])
    npt.assert_(np.max(p_resp,0)[0]>np.max(p_resp,0)[1])
    
    # amps
    npt.assert_(fit.model.m_amp[0]<fit.model.m_amp[1])
    npt.assert_(fit.model.p_amp[0]>fit.model.p_amp[1])
    
    # receptive field
    npt.assert_almost_equal(4.0, fit.receptive_field.sum())
