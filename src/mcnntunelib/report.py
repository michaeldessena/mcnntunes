# -*- coding: utf-8 -*-
"""
Performs MC tunes using Neural Networks
@authors: Stefano Carrazza & Simone Alioli
"""

import os, yoda
import matplotlib.pyplot as plt
from .tools import make_dir, show
import numpy as np
from jinja2 import Environment, PackageLoader, select_autoescape
import mcnntunelib.stats as stats

class Report(object):

    def __init__(self, path):
        """"""
        self.env = Environment(
            loader=PackageLoader('mcnntunelib', 'templates'),
            autoescape=select_autoescape(['html'])
        )

        self.path = path
        make_dir('%s/plots' % self.path)

    def save(self, dictionary):
        """"""
        templates = ['index.html','data.html','model.html','benchmark.html',
                     'minimization.html','raw.html','config.html']

        for item in templates:
            template = self.env.get_template(item)
            output = template.render(dictionary)
            with open('%s/%s' % (self.path, item), 'w') as f:
                f.write(output)

        show('\n- Generated report @ file://%s/%s/index.html' % (os.getcwd(), self.path))

    def plot_minimize(self, minimizer, logger, best_x_unscaled, best_x_scaled, best_error, runs, use_weights=False):
        """"""
        logger.es.plot()
        plt.savefig('%s/plots/minimizer.svg' % self.path)
        plt.close()

        # plot 1d profiles
        N = 40 # points
        for dim in range(runs.x_scaled.shape[1]):
            d = np.linspace(np.min(runs.x_scaled[:,dim]), np.max(runs.x_scaled[:,dim]), N)
            res = np.zeros(N)
            if use_weights: # plot unweighted chi2 for more insight
                unw = np.zeros(N)
            xx = np.zeros(N)
            for i, p in enumerate(d):
                a = np.array(best_x_scaled)
                a[dim] = p
                res[i] = minimizer.chi2(a)
                if use_weights: # plot unweighted chi2 for more insight
                    unw[i] = minimizer.unweighted_chi2(a)
                xx[i] = runs.unscale_x(a)[dim]
            plt.figure()
            if not use_weights:
                plt.plot(xx, res, label='parameter variation', linewidth=2)
            else: # plot unweighted chi2 for more insight
                plt.plot(xx, res, label='parameter variation, weighted $\chi^2$/dof', linewidth=2)
                plt.plot(xx, unw, label='parameter variation, $\chi^2$/dof', linewidth=2)
            plt.axvline(best_x_unscaled[dim], color='r', linewidth=2, label='best value')
            plt.axvline(best_x_unscaled[dim]+best_error[dim], linestyle='--', color='r', linewidth=2, label='1-$\sigma$')
            plt.axvline(best_x_unscaled[dim]-best_error[dim], linestyle='--', color='r', linewidth=2)
            plt.legend(loc='best')
            plt.title('1D profiles for parameter %d - %s' % (dim, runs.params[dim]))
            plt.ylabel('$\chi^2$/dof')
            plt.xlabel('parameter')
            plt.grid()
            plt.yscale('log')
            plt.savefig('%s/plots/chi2_%d.svg' % (self.path, dim))
            plt.close()

    def plot_model(self, models, runs, data):
        """"""
        base = plt.cm.get_cmap('viridis')
        color_list = base(np.linspace(0, 1, len(models)))

        # scatter plot
        plt.figure()
        loss_runs = np.zeros(shape=(len(models), runs.x_scaled.shape[0]))
        diff_runs = np.zeros(shape=(len(models), runs.x_scaled.shape[0]))
        for i, model in enumerate(models):
            for r in range(runs.x_scaled.shape[0]):
                loss_runs[i,r] = model.model.evaluate(runs.x_scaled[r].reshape(1, runs.x_scaled.shape[1]),
                                 runs.y_scaled[r, i].reshape(1), verbose=0)
                diff_runs[i, r] = np.abs(model.predict(runs.x_scaled[r].reshape(1, runs.x_scaled.shape[1])).reshape(1)*runs.y_std[i]+runs.y_mean[i] - runs.y[r, i])/runs.y[r, i]
            #plt.plot([i]*runs.x_scaled.shape[0], loss_runs[i,:], 'o', color=color_list[i])

        bin_loss = []
        for model in models:
            bin_loss.append(model.loss[-1])

        plt.plot(bin_loss, color='k', label='avg. per bin')
        avg_loss = np.mean(bin_loss)
        std_loss = np.std(bin_loss)
        plt.axhline(avg_loss, color='r', linewidth=2, label='total')
        plt.axhline(avg_loss+std_loss, color='r', linestyle='--', label='std. dev.')
        plt.axhline(avg_loss-std_loss, color='r', linestyle='--')
        plt.legend(loc='best')
        plt.xlabel('bin')
        plt.ylabel('MSE')
        plt.title('Loss function for final model (bin-by-bin)')
        plt.grid()
        #plt.yscale('log')
        plt.savefig('%s/plots/model_loss.svg' % self.path)
        plt.close()

        # now plot vs parameters
        for param in range(runs.x.shape[1]):
            plt.figure()
            x = np.zeros(runs.x.shape[0]*len(models))
            y = np.zeros(runs.x.shape[0]*len(models))
            for bin in range(len(models)):
                #x = np.zeros(runs.x.shape[0])
                #y = np.zeros(runs.x.shape[0])
                for r in range(runs.x.shape[0]):
                    x[r+bin*runs.x.shape[0]] = runs.x[r][param]
                    y[r+bin*runs.x.shape[0]] = loss_runs[bin, r]
                #plt.scatter(x, y, marker='o', color=color_list[bin])
            plt.scatter(x, y, marker='o', color='k')
            plt.grid()
            plt.title('Loss function vs %s ' % runs.params[param])
            plt.xlabel('%s' % runs.params[param])
            plt.ylabel('MSE')
            plt.savefig('%s/plots/bounds_%d.svg' % (self.path, param))
            plt.close()

        # now plot the relative differences for the MC
        plt.figure()
        diffs = np.mean(runs.yerr/runs.y, axis=0)*100
        std = np.std(runs.yerr/runs.y, axis=0)*100
        plt.fill_between(range(len(diffs)), diffs-std, diffs+std, color='deepskyblue', edgecolor='deepskyblue', alpha=0.5)
        plt.plot(diffs, color='deepskyblue', linestyle='--', label='MC run mean error')
        nndiffs = np.mean(diff_runs, axis=1)*100
        nnstd = np.std(diff_runs, axis=1)*100
        plt.fill_between(range(len(nndiffs)), nndiffs-nnstd, nndiffs+nnstd, color='orange', edgecolor='orange', alpha=0.5)
        plt.plot(nndiffs, color='orange', linestyle='--', label='Model mean error')
        plt.title('Relative error for MC runs vs Model predictions')
        plt.ylabel('Relative error (%)')
        plt.xlabel('bin')
        plt.ylim([0, np.max(diffs+std)])
        plt.grid()
        plt.legend(loc='best')
        plt.savefig('%s/plots/errors.svg' % self.path)
        plt.close()

        return avg_loss

    def plot_data(self, data, predictions, runs, bestx, display):
        """"""
        hout = []
        ifirst = 0
        for i, hist in enumerate(data.plotinfo):
            size = len(hist['y'])
            rs = [item for item in runs.plotinfo if item['title'] == hist['title']]
            up = np.vstack([r['y'] for r in rs]).max(axis=0)
            dn = np.vstack([r['y'] for r in rs]).min(axis=0)
            reperr = np.mean([r['yerr'] for r in rs], axis=0)

            plt.figure()
            plt.subplot(211)

            plt.fill_between(hist['x'], dn, up, color='#ffff00')

            plt.errorbar(hist['x'], hist['y'], yerr=hist['yerr'],
                         marker='o', linestyle='none', label='data')

            plt.plot(hist['x'], predictions[ifirst:ifirst+size], '-', label='best model')

            plt.yscale('log')
            plt.legend(loc='best')
            plt.title(hist['title'])

            plt.subplot(212)

            plt.errorbar(hist['x'], hist['y']/hist['y'], yerr=hist['yerr']/hist['y'],
                         marker='o', linestyle='none', label='data')
            plt.plot(hist['x'], predictions[ifirst:ifirst+size]/hist['y'], '-', label='best model')

            plt.savefig('%s/plots/%d_data.svg' % (self.path, i))
            plt.close()

            # add to yoda
            h = yoda.Scatter2D(path=hist['title'])
            for t, p in enumerate(runs.params):
                h.setAnnotation(p, bestx[t])
            for p in range(size):
                h.addPoint(hist['x'][p], predictions[ifirst:ifirst+size][p], [hist['xerr-'][p], hist['xerr+'][p]])
            hout.append(h)

            # calculate chi2
            for j, element in enumerate(display):
                if element['name'] == hist['title']: 
                    display[j]['model'] = stats.chi2(predictions[ifirst:ifirst+size], hist['y'],
                                                    np.square(hist['yerr'])+np.square(reperr))
                elif element['name'] == hist['title']+" (weighted)":
                    display[j]['model'] = stats.chi2(predictions[ifirst:ifirst+size], hist['y'],
                                                    np.square(hist['yerr'])+np.square(reperr), weights=hist['weight'])


            ifirst += size

        yoda_path = '%s/best_model.yoda' % self.path
        show('\n- Exporting YODA file with predictions in %s' % yoda_path)
        yoda.write(hout, yoda_path)

    def plot_correlations(self, corr):
        """"""
        plt.figure()
        plt.imshow(corr, cmap='Spectral', interpolation='nearest', vmin=-1, vmax=1)
        plt.colorbar()
        plt.savefig('%s/plots/correlations.svg' % self.path)
        plt.close()

    def plot_benchmark(self, benchmark_results):
        """"""
        # Iterate over the number of parameters
        for index1 in range(len(benchmark_results['single_closure_test_results'][0]['details'])):

            # Get parameter name
            param_name = benchmark_results['single_closure_test_results'][0]['details'][index1]['params']

            true_parameter = np.zeros(len(benchmark_results['single_closure_test_results']))
            relative_error = np.zeros(len(benchmark_results['single_closure_test_results']))

            # Iterate over  the number of closure tests
            for index2 in range(len(benchmark_results['single_closure_test_results'])):

                # Calculate the relative error
                true_parameter[index2] = benchmark_results['single_closure_test_results'][index2]['details'][index1]['true_params']
                relative_error[index2] = abs((benchmark_results['single_closure_test_results'][index2]['details'][index1]['predicted_params']-
                                         true_parameter[index2]) / true_parameter[index2]) * 100
            
            # Plot
            plt.figure()
            plt.scatter(true_parameter, relative_error, color='k')
            plt.title("Relative difference on %s" % param_name)
            plt.xlabel("%s" % param_name)
            plt.ylabel('Relative difference (%)')
            plt.grid(True)
            plt.savefig('%s/plots/benchmark_%s.svg' % (self.path, param_name))
            plt.close()