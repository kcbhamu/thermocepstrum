#!/usr/bin/env python

from thermocepstrum.utils.utils import PrintMethod
log = PrintMethod()
import sys
import os
import math
import thermocepstrum as tc
import numpy as np
import scipy as sp
import scipy.stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator

try:
    import pkg_resources
    pltstyle_filename = pkg_resources.resource_filename('thermocepstrum.utils', 'plot_style.mplstyle')
except:
    # fallback (maybe it is not installed...)
    try:
        abs_path = os.path.abspath(__file__)
        tc_path = abs_path[:abs_path.rfind('/')]
        path.append(tc_path[:tc_path.rfind('/')])
    except:
        abs_path = '.'
    pltstyle_filename = tc_path + '/utils/plot_style.mplstyle'
try:
    plt.style.use(pltstyle_filename)
except:
    pass

c = plt.rcParams['axes.prop_cycle'].by_key()['color']


try:
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
except:
    log.write_log('Error: cannot import inset_axes (will not be able to plot some parts of the plots)')


def main():
    usage = """usage: {} output N_currents N_processes DT_FS max_THz nyquist k_SI_max zoom_max_THz zoom_k_SI_max input1 input2 ... inputN

        N must be at least 2.
        This utility computes some histograms and statistics of the outputs generated by the analysis program.
        N_processes is the number of independent processes used, and N_currents is the number of currents in every random process.
        DT_FS is the timestep in femtoseconds.

        Riccardo Bertossa (SISSA), 2018

     """.format(sys.argv[0])

    #number of elements of the periodogram used in making the big histogram
    all_cut = 1500

    if len(sys.argv) < 8:
        log.write_log(usage)
        exit(-1)

    output = sys.argv[1]
    M = int(sys.argv[2])
    L = int(sys.argv[3])
    dof = L - M + 1
    log.write_log(dof, ' degrees of freedom for the chi2 distribution')
    DT_FS = float(sys.argv[4])
    max_THz = float(sys.argv[5])
    nyq = float(sys.argv[6])
    k_SI_max = float(sys.argv[7])
    zmax_THz = float(sys.argv[8])
    zk_SI_max = float(sys.argv[9])
    ff = 10
    ndata = len(sys.argv) - ff

    log.write_log('Number of inputs: {}\n reading...'.format(ndata))
    periodograms = []
    cospectrums = []
    cepstrals = []
    aic_Kmins = np.zeros(ndata)
    kappas_Kmin = np.zeros(ndata)
    kappas_Kmin_std = np.zeros(ndata)
    kappa_scales = np.zeros(ndata)
    l0s = np.zeros(ndata)
    l0s_std = np.zeros(ndata)
    if os.path.isfile(sys.argv[ff] + '.psd.npy'):
        freqs = np.load(sys.argv[ff] + '.psd.npy')[0]
    else:
        freqs = np.loadtxt(sys.argv[ff] + '.psd.dat', usecols=(0,), unpack=True)
    cont = 0
    for fname in sys.argv[ff:]:
        if os.path.isfile(fname + '.psd.npy'):
            periodograms.append(np.load(fname + '.psd.npy')[3:5])
        else:
            periodograms.append(np.loadtxt(fname + '.psd.dat', usecols=(3, 4), unpack=True))
        if periodograms[-1].shape != periodograms[0].shape:
            log.write_log(fname, ' not used (inconsistent shape with firts element)', periodograms[-1].shape,
                          periodograms[0].shape)
            del periodograms[-1]
            continue
        if os.path.isfile(fname + '.cepstral.npy'):
            cepstrals.append(np.load(fname + '.cepstral.npy')[[4, 5, 2, 3]])
        else:
            cepstrals.append(np.loadtxt(fname + '.cepstral.dat', usecols=(4, 5), unpack=True))

        if os.path.isfile(fname + '.cospectrum.npy'):
            cospectrums.append(np.load(fname + '.cospectrum.npy')[1] / L)
        elif os.path.isfile(fname + '.cospectrum.dat'):
            cospectrums.append(np.loadtxt(fname + '.cospectrum.npy')[1] / L)

        if len(cospectrums) == 0:
            cospectrums = None

        fka = open(fname + '.kappa_scale_aicKmin.dat')
        kappa_scales[cont] = float(fka.readline())
        aic_Kmin = int(fka.readline())
        aic_Kmins[cont] = aic_Kmin
        fka.close()

        kappas_Kmin[cont] = cepstrals[cont][0, aic_Kmin]
        kappas_Kmin_std[cont] = cepstrals[cont][1, aic_Kmin]
        l0s[cont] = cepstrals[cont][2, aic_Kmin]
        l0s_std[cont] = cepstrals[cont][3, aic_Kmin]
        log.write_log(fname, periodograms[cont].shape, cepstrals[cont].shape)
        cont += 1

    aic_KminM = np.mean(aic_Kmins)
    aic_Kmin = int(aic_KminM)
    log.write_log('Reading done.')

    #resizing and creating a big numpy array.
    #for periodogram,cepstral in zip(periodograms,cepstrals):
    for i in range(1, len(periodograms)):
        periodograms[i].resize(periodograms[0].shape)
        cepstrals[i].resize(cepstrals[0].shape)
    # *this does not work when using a lot of data
    #import pdb; pdb.set_trace()
    #log.write_log(periodograms[0].shape)
    #for i in range(1,len(periodograms)):
    #    log.write_log i
    #    periodograms[i]=np.resize(periodograms[i],periodograms[0].shape)
    #    cepstrals[i]=np.resize(cepstrals[i],cepstrals[0].shape)

    cepstrals = np.array(cepstrals, copy=False)
    periodograms = np.array(periodograms, copy=False)

    log = open(output + '.log', 'w')

    log.write('Mean value of kappa_scale: {}\n'.format(np.mean(kappa_scales)))
    log.write('Mean value of minimum of AIC: {}\n'.format(aic_KminM))
    log.write('\n')
    log.write('Mean value and standard deviation of kappa(aic_Kmin):                    {} +/- {}\n'.format(
        np.mean(kappas_Kmin), np.std(kappas_Kmin)))
    log.write('Mean value of calculated statistical error per block of kappa(aic_Kmin): {}\n'.format(
        np.mean(kappas_Kmin_std)))
    log.write('\n')
    log.write('Mean value and standard deviation of L0(aic_Kmin):                       {} +/- {}\n'.format(
        np.mean(l0s), np.std(l0s)))
    log.write('Mean value of calculated statistical error per block of L0(aic_Kmin):    {}\n'.format(np.mean(l0s_std)))
    log.write('\n\n===========')
    log.write('Values at mean value of aic_Kmin:\n')
    log.write('\n')
    log.write('Mean value and standard deviation of kappa(aic_Kminm):                   {} +/- {}\n'.format(
        np.mean(cepstrals[:, 0, aic_Kmin]), np.std(cepstrals[:, 0, aic_Kmin])))
    log.write('Mean value of calculated statistical error per block of kappa(aic_Kmin): {}\n'.format(
        np.mean(cepstrals[:, 1, aic_Kmin])))
    log.write('\n')
    log.write('Mean value and standard deviation of L0(aic_Kmin):                       {} +/- {}\n'.format(
        np.mean(cepstrals[:, 2, aic_Kmin]), np.std(cepstrals[:, 2, aic_Kmin])))
    log.write('Mean value of calculated statistical error per block of L0(aic_Kmin):    {}\n'.format(
        np.mean(cepstrals[:, 3, aic_Kmin])))
    log.close()

    #calculate statistics over first axis
    std_periodogram = np.std(periodograms, axis=0, ddof=1)
    std_cepstral = np.std(cepstrals, axis=0, ddof=1)
    mean_periodogram = np.mean(periodograms, axis=0)
    mean_cospectrum = None
    if cospectrums != None:
        mean_cospectrum = np.mean(cospectrums, axis=0)
    mean_cepstral = np.mean(cepstrals, axis=0)
    log.write_log(mean_cepstral.shape)
    log.write_log(mean_periodogram.shape)
    np.savetxt(output + '.mean_periodogram',
               np.c_[freqs, mean_periodogram[0], std_periodogram[0], mean_periodogram[1], std_periodogram[1]])
    np.savetxt(output + '.mean_cepstral', np.c_[mean_cepstral[0], std_cepstral[0], mean_cepstral[1], std_cepstral[1]])

    log.write_log('Mean values and standard deviations done.')

    log.write_log('Computing index of .40 psd power...')
    psd_int = np.cumsum(mean_periodogram[0])
    psd_int = psd_int / psd_int[-1]
    p95 = 0
    while psd_int[p95] < 0.10:
        p95 = p95 + 1
    all_cut = p95

    all_cut = 100

    #select only components that are significantly different from zero
    selection_not_zero = []
    zero = mean_periodogram[0, 0] / 10
    for i in range(all_cut):
        if mean_periodogram[0, i] > zero:
            selection_not_zero.append(i)
    log.write_log('Number of components > {}: {}. Last is {}'.format(zero, len(selection_not_zero),
                                                                     selection_not_zero[-1]))
    #     log.write_log(selection_not_zero)

    log.write_log('Index = {} , {} THz'.format(p95, freqs[p95]))

    log.write_log('Some plots...')
    #make some plots and histograms

    with PdfPages(output + '_all.pdf') as pdf:
        plt.fill_between(freqs, mean_periodogram[0] - std_periodogram[0], mean_periodogram[0] + std_periodogram[0])
        plt.plot(freqs, mean_periodogram[0])
        plt.title('Original PSD')
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        class Psd:
            psd = None
            mpsd = None
            fpsd = None
            freqs_THz = None
            kappa_scale = None
            cospectrum = None
            mcospectrum = None
            ucospectrum = None
            DT_FS = None

            def ffpsd(self, w, single=False):
                WF = int(round(w / 1000. * self.DT_FS * len(self.freqs_THz) * 2.))
                log.write_log('filtering: ', WF)
                if not single:
                    ffpsd = tc.md.tools.runavefilter(self.mpsd, WF)
                else:
                    ffpsd = tc.md.tools.runavefilter(self.psd, WF)
                self.fpsd = ffpsd
                try:
                    for i in range(self.ucospectrum.shape[0]):
                        for j in range(self.ucospectrum.shape[1]):
                            if not single:
                                ffc = tc.md.tools.runavefilter(self.mcospectrum[i, j], WF)
                            else:
                                ffc = tc.md.tools.runavefilter(self.ucospectrum[i, j], WF)
                            self.cospectrum[i, j] = ffc
                except AttributeError:
                    pass

        psd = Psd()

        psd.DT_FS = DT_FS
        psd.kappa_scale = np.mean(kappa_scales) / DT_FS
        psd.freqs_THz = freqs
        plot_idx = 2
        psd.psd = periodograms[plot_idx, 0, :]
        psd.mpsd = mean_periodogram[0, :]
        psd.fpsd = np.copy(mean_periodogram[0, :])
        psd.ucospectrum = cospectrums[plot_idx]
        psd.mcospectrum = mean_cospectrum
        psd.cospectrum = np.copy(mean_cospectrum)

        plt_psd(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt_psd_with_zoom(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max, inset_maxTHz=zmax_THz,
                          inset_maxk=zk_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, np.real(psd.cospectrum[1, 0]))
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()
        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, psd.cospectrum[1, 1])
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        psd.ffpsd(0.5, single=True)

        plt_psd(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt_psd_with_zoom(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max, inset_maxTHz=zmax_THz,
                          inset_maxk=zk_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, np.real(psd.cospectrum[1, 0]))
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()
        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, psd.cospectrum[1, 1])
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        psd.ffpsd(0.2, single=False)

        plt_psd(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt_psd_with_zoom(psd, k_00=True, f_THz_max=max_THz, nyq=nyq, k_SI_max=k_SI_max, inset_maxTHz=zmax_THz,
                          inset_maxk=zk_SI_max)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, np.real(psd.cospectrum[1, 0]))
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()
        plt.xlim([0, max_THz])

        plt.plot(psd.freqs_THz, psd.cospectrum[1, 1])
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        #make histogram for component 0 and 1 of psd

        #compute means without i-th element
        independent_mean = np.zeros((periodograms.shape[0], periodograms.shape[2]))
        for i in range(periodograms.shape[0]):
            all_but_ith = [x for x in range(periodograms.shape[0]) if x != i]
            independent_mean[i, :] = np.mean(periodograms[all_but_ith, 0, :], axis=0)

        plt.hist(kappas_Kmin)
        plt.title('kappa(aic-Kmin)')
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        data1 = periodograms[:, 0, 0] / independent_mean[:, 0]

        ks__0 = plt_hist_single_psd(data1, dof)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        data2 = periodograms[:, 0, 1] / independent_mean[:, 1]
        ks__1 = plt_hist_single_psd(data2, dof * 2)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        #ks_1=sp.stats.kstest(data2*2*dof,sp.stats.chi2(2*dof).cdf)

        #make histogram for all components normalized
        all_normalized = np.zeros(periodograms.shape[0] * (len(selection_not_zero)))
        for i in range(periodograms.shape[0]):
            #for idx,i in enumerate(selection_not_zero):
            all_normalized[i * len(selection_not_zero):(i + 1) *
                           len(selection_not_zero
                              )] = periodograms[i, 0, selection_not_zero] / independent_mean[i, selection_not_zero]

        ks_all = plt_hist_single_psd(all_normalized, dof * 2, nbins=100)
        pdf.savefig(bbox_inches='tight', pad_inches=0.0)
        plt.close()

        #         np.savetxt(output+'.histogram_all',np.c_[(intervals[1:]+intervals[:-1])/2.0,histogram/np.sum(histogram)])
        #         log.write_log('Histogram bin width: {}'.format(intervals[1]-intervals[0]))

        #         np.savetxt(output+'.kolmogorov_smirnov',[ks_0,ks_1,ks_all])
        log.write_log('Statistical test results (psd(0), psd(1), psd(all but 0)): {}'.format([ks__0, ks__1, ks_all]))

        #make graphs of mean of theoretical and statistical error of the final result
        plt.fill_between(np.arange(mean_cepstral.shape[1]), mean_cepstral[0] - std_cepstral[0],
                         mean_cepstral[0] + std_cepstral[0])
        plt.plot(np.arange(mean_cepstral.shape[1]), mean_cepstral[0] - mean_cepstral[1])
        plt.plot(np.arange(mean_cepstral.shape[1]), mean_cepstral[0] + mean_cepstral[1])
        plt.plot(np.arange(mean_cepstral.shape[1]), mean_cepstral[0])
        plt.title('Convergence of cepstral result with theoretical and statistical errors')

        plt.xlim([0, 10 * aic_Kmin])
        max_y = np.amax((mean_cepstral[0] + std_cepstral[0])[aic_Kmin:3 * aic_Kmin])
        min_y = np.amin((mean_cepstral[0] - std_cepstral[0])[aic_Kmin:3 * aic_Kmin])
        plt.ylim([min_y * 0.8, max_y * 1.2])

        pdf.savefig(bbox_inches='tight')
        plt.close()


def plt_hist_single_psd(data1, dof, nbins=None):

    fig = plt.figure(figsize=(3.8, 2.3))
    if nbins != None:
        h, i, p = plt.hist(data1 * dof, bins=nbins, normed=True)
    else:
        h, i, p = plt.hist(data1 * dof, normed=True)

    xmax = i[-1]
    ymax = np.max(h) * 1.2
    plt.xlim([0.0, xmax])
    plt.ylim([0.0, ymax])

    x = np.linspace(0.0, xmax, 1000)

    plt.plot(x, sp.stats.chi2.pdf(x, dof), ls=':', label='$\chi^2_{{{}}}$'.format(dof))

    plt.xlabel('Normalized values')
    plt.ylabel('Probability')
    plt.legend()

    dx1, dx2 = n_tick_in_range(0, xmax, 5)
    dy1, dy2 = n_tick_in_range(0, ymax, 5)

    plt.axes().xaxis.set_major_locator(MultipleLocator(dx1))
    plt.axes().xaxis.set_minor_locator(MultipleLocator(dx2))
    plt.axes().yaxis.set_major_locator(MultipleLocator(dy1))
    plt.axes().yaxis.set_minor_locator(MultipleLocator(dy2))
    ks_0 = sp.stats.kstest(data1 * dof, sp.stats.chi2(dof).cdf)

    text = 'KS-value=${}$\nP=${}$'.format(as_si(ks_0[0], 1), as_si(ks_0[1], 1))
    plt.text(.5, .6, text, transform=fig.transFigure)

    return ks_0


def plt_psd_with_zoom(jf, j2=None, j2pl=None, f_THz_max=None, k_SI_max=None, k_00=False, nyq=None, inset_maxTHz=None,
                      inset_maxk=None):
    #plt.axes([0,1,0,1])
    fig_r, ax0 = plt_psd(jf, j2, j2pl, f_THz_max, k_SI_max, k_00, nyq)
    coord_f = [0.23, 0.55, 0.3, 0.3]
    ax = fig_r.add_axes(coord_f)
    inv = fig_r.transFigure   # + ax0.transData.inverted()
    f_x = 0.72
    f_x2 = 1.25
    f_y = 0.87
    f_y2 = 1.35
    log.write_log(inv.transform((coord_f[0] * f_x, coord_f[1] * f_y)))
    ax0.add_patch(
        matplotlib.patches.Rectangle((coord_f[0] * f_x, coord_f[1] * f_y), coord_f[2] * f_x2, coord_f[3] * f_y2,
                                     fill=True, color='White', visible=True, transform=inv))
    #plt.box()
    plt_psd(jf, j2, j2pl, inset_maxTHz, inset_maxk, k_00, nyq, False, axes=ax)


def plt_psd(jf, j2=None, j2pl=None, f_THz_max=None, k_SI_max=None, k_00=False, nyq=None, plt_figure=True, axes=None):

    if f_THz_max == None:
        idx_max = index_cumsum(jf.psd, 0.95)
        f_THz_max = jf.freqs_THz[idx_max]

    if k_SI_max == None:
        k_SI_max = np.max(
            jf.fpsd[:int(jf.freqs_THz.shape[0] * f_THz_max / jf.freqs_THz[-1])] * jf.kappa_scale * .5) * 1.3
        if k_00:
            try:
                k_SI_max2 = np.max(
                    np.real(jf.cospectrum[0, 0][:int(jf.freqs_THz.shape[0] * f_THz_max / jf.freqs_THz[-1])]) *
                    jf.kappa_scale * .5) * 1.3
                if k_SI_max < k_SI_max2:
                    k_SI_max = k_SI_max2
            except AttributeError:
                pass

    fig_r = None
    if plt_figure:
        fig_r = plt.figure(figsize=(3.4, 2.0))
    if axes is None:
        axes = plt.gca()

    axes.plot(jf.freqs_THz, jf.psd * jf.kappa_scale * .5, lw=0.2, c='0.8', zorder=0)
    axes.plot(jf.freqs_THz, jf.fpsd * jf.kappa_scale * .5, c=c[0], zorder=2)
    if j2 != None:
        axes.axvline(x=j2.Nyquist_f_THz, ls='--', c='k', dashes=(1.4, 0.6), zorder=3)
    if j2pl != None:
        axes.plot(j2pl.freqs_THz, j2pl.dct.psd * j2pl.kappa_scale * .5, c=c[2])
    try:
        axes.plot(jf.freqs_THz, np.real(jf.cospectrum[0, 0]) * jf.kappa_scale * .5, c=c[3], lw=1.0, zorder=1)
    except AttributeError:
        pass

    axes.set_ylim(0, k_SI_max)
    axes.set_xlim(0, f_THz_max)
    if plt_figure:
        axes.set_xlabel(r'$\omega/2\pi$ (THz)')
        #     axes.set_ylabel('$^{\ell M}\widehat{S}\'_{\,k}$ (W/mK)')
        axes.set_ylabel(r'W/(m$\,$K)')
    idxnyq = int(nyq / jf.freqs_THz[-1] * jf.freqs_THz.size)
    if nyq != None and nyq < f_THz_max:
        axes.annotate('', xy=(nyq, (k_SI_max-jf.fpsd[idxnyq]*jf.kappa_scale*.5)/7+jf.fpsd[idxnyq]*jf.kappa_scale*.5), \
                     xytext=(nyq, (k_SI_max-jf.fpsd[idxnyq]*jf.kappa_scale*.5)/7+jf.fpsd[idxnyq]*jf.kappa_scale*.5+k_SI_max/7.0), \
                     arrowprops={'width': 1.0, 'headwidth': 3.0, 'headlength': 7, 'color': 'k'})

    ntick = 5
    if axes is not None:
        ntick = 3
    dx1, dx2 = n_tick_in_range(0, f_THz_max, ntick)
    dy1, dy2 = n_tick_in_range(0, k_SI_max, ntick)
    #dx1=10
    #dx2=5
    axes.xaxis.set_major_locator(MultipleLocator(dx1))
    axes.xaxis.set_minor_locator(MultipleLocator(dx2))
    axes.yaxis.set_major_locator(MultipleLocator(dy1))
    axes.yaxis.set_minor_locator(MultipleLocator(dy2))
    return fig_r, axes


def n_tick_in_range(beg, end, n, n_c=1, nit=0):
    size = end - beg
    dx0 = (end - beg) / n
    e = 10**(math.ceil(math.log10(dx0)))
    m = dx0 / e
    cifre0 = math.ceil(m * 10**(n_c))
    cifre = cifre0 - cifre0 % 5
    if cifre == 0:
        cifre = 1.0
    delta = cifre * e / 10**(n_c)
    #log.write_log("n=",n, " dx0=",dx0," e=",e," m=" ,m," cifre=", cifre)
    if nit < 30:
        if delta >= size:
            return n_tick_in_range(beg, end, n + 1, n_c, nit + 1)
        if (end - beg) / delta > n and n > 1:
            return n_tick_in_range(beg, end, n - 1, n_c, nit + 1)

    return delta, delta / 2


def index_cumsum(arr, p):
    if (p > 1 or p < 0):
        raise ValueError('p must be between 0 and 1')
    arr_int = np.cumsum(arr)
    arr_int = arr_int / arr_int[-1]
    idx = 0
    while arr_int[idx] < p:
        idx = idx + 1
    return idx


def as_si(x, ndp):
    s = '{x:0.{ndp:d}e}'.format(x=x, ndp=ndp)
    try:
        m, e = s.split('e')
    except ValueError:
        return r'0\times 10^{\infty}'
    return r'{m:s}\times 10^{{{e:d}}}'.format(m=m, e=int(e))


if __name__ == '__main__':
    main()
