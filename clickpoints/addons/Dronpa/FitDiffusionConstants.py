#!/usr/bin/env python
# -*- coding: utf-8 -*-
# FitDiffusionConstants.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function
from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import minimize

import theano.tensor as T
import theano
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import TheanoExpm

theano.config.compute_test_value = 'warn'


def TGetAfromD(D, decay, link_pairs, N, areas):
    """
         Create a matrix A that describes the equation system: dI/dt = A*I
    """
    # initialize an empty matrix
    A = T.zeros([N, N], dtype=theano.config.floatX)
    # add the inflows from the diffusive links
    for j in range(len(link_pairs)):
        link1 = link_pairs[j][0]
        link2 = link_pairs[j][1]
        # add the diffusion constant on both cells as input
        A = T.set_subtensor(A[link1, link2], D[j])
        A = T.set_subtensor(A[link2, link1], D[j])
    # add the outflows
    for i in range(N):
        # the outflow is the sum of all inflows in the neighbour cells
        A = T.set_subtensor(A[i, i], -T.sum(A[i, :]))
    # norm values such that total amount is conserved
    A = A / np.array([areas] * N)
    # add loss term
    for i in range(N):
        # for each cell on its diagonal
        A = T.set_subtensor(A[i, i], A[i, i] - decay)
    # return the matrix
    return A


def GetModel(times, data, link_pairs, N, areas):
    global shared_I0, shared_It
    # start intensity I_0
    shared_I0 = theano.shared(data[0, :], 'I0')
    I0 = shared_I0
    # intensity change over time I_t
    shared_It = theano.shared(data, 'It')
    It = shared_It
    # fit parameters
    p = T.dvector('p')
    p.tag.test_value = np.random.rand(len(link_pairs) + 1) * 0.01 + 0.1
    # split fit parameters in diffusion and loss term
    D = p[:-1]
    decay = p[-1]
    # transform diffusion constants to a link matrix
    A = TGetAfromD(D, decay, link_pairs, N, areas)
    # prepare lists for iteration
    powerA = []
    I = [I0]
    cost = 0
    # iterate over the given times to solve the equation at different times
    for i in range(1, len(times)):
        # Matrix exponential function
        powerA.append(TheanoExpm.Expm()(A * times[i]))  # assume t = 1
        # multiply with starting values
        I.append(T.dot(powerA[-1], I0))  # [cell_mask]
        # cost is the sum of the squared differences plus a small renormalisation term keeping the parameter values down
        cost += T.sum((It[i, :] / 1000. - I[-1] / 1000.) ** 2) + 0.0001 * T.sum(p ** 2)

    # compile function that takes the parameter values and outputs the intensities at the given times
    Model = theano.function(inputs=[p], outputs=I)
    # compile function that returns cost and gradient
    grad = T.grad(cost, p)
    ModelCost = theano.function(inputs=[p], outputs=[cost, grad])

    # return the two functions
    return ModelCost, Model

def saveToExcel(name, link_pairs, cell_names, cell_indices, p):
    import xlwt
    wb = xlwt.Workbook()
    wb_sheet = wb.add_sheet('data')

    # write xls header
    wb_sheet.write(0, 0, "Cell A")
    wb_sheet.write(0, 1, "Cell B")
    wb_sheet.write(0, 2, "Diffusion Constant")
    for index, pair in enumerate(link_pairs):
        print(cell_names)
        wb_sheet.write(index+1, 0, cell_names[cell_indices[pair[0]]])
        wb_sheet.write(index+1, 1, cell_names[cell_indices[pair[1]]])
        wb_sheet.write(index+1, 2, p[index])
    wb.save(name)

def plotIntensity(N, times, I, data, areas, cell_names, cell_indices, cell_errors, colors):
    plt.plot([], [], 'ko', label="data")
    plt.plot([], [], 'k-', label="fit")
    for m in range(N):
        plt.errorbar(times, data[:, m] / areas[m], yerr=cell_errors[m], color=colors[m])
    plt.xlabel("time (min)")
    plt.ylabel("mean intensity")
    plt.legend()
    return colors


def plotIntensityFit(N, times, I, data, areas, cell_names, cell_indices, colors):
    plt.plot([], [], 'ko', label="data")
    plt.plot([], [], 'k-', label="fit")
    for m in range(N):
        line, = plt.plot(times, I[:, m] / areas[m], color=colors[m])  # , linestyle=styles[m % len(styles)])
        plt.plot(times, data[:, m] / areas[m], 'o', color=colors[m])
    plt.xlabel("time (min)")
    plt.ylabel("mean intensity")
    plt.legend()
    return colors

def plotImageWithDiffusionConstans(output_folder, db, p, N, link_pairs, colors):
    # load centers
    centers = np.loadtxt(os.path.join(output_folder, "cell_centers.txt"))
    centers = np.array(centers)[:N, :]

    # plot centers
    for m in range(N):
        plt.plot(centers[m, 0], centers[m, 1], 'o', color=colors[m % len(colors)], ms=20)

    # plot image
    im1 = db.getImage(0).data
    plt.imshow(im1)

    # plot links
    i = 0
    for link in link_pairs:
        # connection lines
        plt.plot([centers[link[0]][0], centers[link[1]][0]], [centers[link[0]][1], centers[link[1]][1]], '--w',
                 alpha=0.5)
        # diffusion constant
        plt.text(np.mean([centers[link[0]][0], centers[link[1]][0]]),
                 np.mean([centers[link[0]][1], centers[link[1]][1]]),
                 "%.2f" % p[i], color="w", va='center', ha='center')
        # text(mean([centers[link[0]][0], centers[link[0]][0], centers[link[1]][0]]), mean([centers[link[0]][1], centers[link[0]][1], centers[link[1]][1]]), "%.2f"%p[i], color="w", va='center', ha='center')
        # text(mean([centers[link[0]][0], centers[link[1]][0], centers[link[1]][0]]), mean([centers[link[0]][1], centers[link[1]][1], centers[link[1]][1]]), "%.2f"%p[i+len(link_pairs)], color="w", va='center', ha='center')
        i += 1

    xwidth = np.max(centers[:, 0]) - np.min(centers[:, 0])
    ywidth = np.max(centers[:, 1]) - np.min(centers[:, 1])
    # cut image to show only the cells of interest
    plt.xlim(np.min(centers[:, 0]) - 50, np.max(centers[:, 0]) + 50)
    plt.ylim(np.max(centers[:, 1]) + 50, np.min(centers[:, 1]) - 50)

def resultsPlot(output_folder, db, N, times, I, data, areas, p, link_pairs, cell_names, cell_indices, colors, cell_errors):
    # create figure
    plt.figure(1, (15, 6))
    plt.clf()
    # plot intensities with fit
    plt.subplot(121)

    plotIntensity(N, times, I, data, areas, cell_names, cell_indices, cell_errors, colors)
    # plot image
    plt.subplot(122)
    plotIntensityFit(N, times, I, data, areas, cell_names, cell_indices, colors)
    #plotImageWithDiffusionConstans(output_folder, db, p, N, link_pairs, colors)
    # save and show
    plt.savefig(os.path.join(output_folder, "Fit.png"))

def fitDiffusionConstants(db, output_folder):
    cell_indices = np.loadtxt(os.path.join(output_folder, "cell_indices.txt")).tolist()

    cell_names = {cell.index: cell.name for cell in db.getMaskTypes()}

    mask = db.getImage(0).mask.data
    connections = db.getLines(type="connect")
    link_pairs = []
    for connection in connections:
        pair1 = mask[int(connection.y1), int(connection.x1)]
        pair2 = mask[int(connection.y2), int(connection.x2)]
        try:
            pair1 = cell_indices.index(pair1)
            pair2 = cell_indices.index(pair2)
        except ValueError:
            print("Invalid connection!")
            continue
        link_pairs.append([pair1, pair2])
        print(link_pairs)

    data = np.loadtxt(os.path.join(output_folder, "cell.txt"))
    errors = np.loadtxt(os.path.join(output_folder, "cell_error.txt"))
    times = data[:, 0]
    N = data.shape[1]-1
    areas = np.loadtxt(os.path.join(output_folder, "cell_sizes.txt"))[:N]
    data = data[:, 1:N + 1] * areas
    print(data.shape)
    print(areas.shape)

    print("Building Model")
    ModelCost, Model = GetModel(times, data, link_pairs, N, areas)
    print("Building Model -- finished")

    if 0:
        # random starting values
        p = np.random.rand(len(link_pairs) + 1) * 5 + 20
        # find best diffusion constants
        print("Minimize Model")
        res = minimize(ModelCost, p, method='L-BFGS-B', jac=True, options={'disp': True, 'maxiter': int(1e5)},
                       bounds=((0, None),) * len(p))
        p = res['x']
        # save results
        saveToExcel(os.path.join(output_folder, "diffusion_constants.xls"), link_pairs, cell_names, cell_indices, p)
        np.savetxt(os.path.join(output_folder, "diffusion_constants.txt"), p)
    else:
        p = np.loadtxt(os.path.join(output_folder, "diffusion_constants.txt"))
        saveToExcel(os.path.join(output_folder, "diffusion_constants.xls"), link_pairs, cell_names, cell_indices, p)
    I = np.array(Model(p))

    colors = [mask_type.color for mask_type in db.getMaskTypes()]
    print("colors", colors)

    resultsPlot(output_folder, db, N, times, I, data, areas, p, link_pairs, cell_names, cell_indices, colors, errors)
    plt.show()
