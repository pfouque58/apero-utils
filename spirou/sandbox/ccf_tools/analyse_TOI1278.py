import numpy as np
import matplotlib.pyplot as plt
from astropy.table import Table
from bisector import *
from astropy.time import Time
from ccf2rv import *
from per_epoch_table import per_epoch_table

def sinusoidal(phase,dphase,amp,zp):
    return np.sin( (phase+dphase))*amp+zp

# do not *formally* exclude an order, but this is done later with the bandpass keyword
exclude_orders = [-1]

object = 'TOI-1278'

# number of median-absolute deviations within an epoch to consider a point discrepant

tbl = get_object_rv(object,mask = 'gl846_neg',
                    method = 'template',force = True,
                    exclude_orders = exclude_orders,
                    snr_min = 20.0, sanitize = False,
                    dvmax_per_order = 3.0, bandpass = 'HK',
                    doplot = True)

# period for the sinusoidal currve
period = 14.4

# create the table with bis per epoch
tbl_bin = per_epoch_table(tbl,nMAD_cut = 5)

# get time stamps friendly for plotting
t2 = Time(tbl_bin['MJDATE_MEAN'], format = 'mjd')
t3 = Time(tbl['MJDATE'], format = 'mjd')

# get phase for sine fitting
phase_bin = 2*np.pi*tbl_bin['MJDATE_MEAN']/period
phase = 2*np.pi*tbl['MJDATE']/period

# fit sinusoid
fit, pcov = curve_fit(sinusoidal, phase_bin, tbl_bin['RV'])

# some plotting fiddling
dt = np.max(tbl_bin['MJDATE_MEAN']) - np.min(tbl_bin['MJDATE_MEAN'])
time_plot = np.arange(np.min(tbl_bin['MJDATE_MEAN'])-dt/10,np.max(tbl_bin['MJDATE_MEAN'])+dt/10,dt/1000)
phase_plot = 2*np.pi*time_plot/period

model_bin =  sinusoidal(phase_bin,*fit)
model=  sinusoidal(phase,*fit)
model_plot =  sinusoidal(phase_plot,*fit)

print('Amplitude of the sinusoidal at {0} days: {1} m/s'.format(period,fit[1]))
print('Mean/Median per-epoch STDDEV {0}/{1} m/s'.format(np.mean(tbl_bin["ERROR_RV"]),np.median(tbl_bin["ERROR_RV"])))

fig, ax = plt.subplots(nrows = 2, ncols = 1,sharex = True)

for i in range(len(t2)):
    ax[0].plot_date(t2.plot_date,tbl_bin['RV'],'g.')
    ax[0].plot_date([t2[i].plot_date,t2[i].plot_date],[tbl_bin['RV'][i]-tbl_bin['ERROR_RV'][i],
                                                       tbl_bin['RV'][i]+tbl_bin['ERROR_RV'][i]],'g')

ax[0].plot_date(t3.plot_date,tbl['RV'],'r.',alpha = 0.5)
ax[1].errorbar(t3.plot_date,tbl['RV'] - model,yerr=tbl['ERROR_RV'], linestyle="None",
               fmt='o',color = 'green', alpha = 0.2)

ax[0].plot(Time(time_plot, format = 'mjd').plot_date,model_plot,'r:')
ax[0].set(ylabel = 'Velocity [km/s]',title = object)


ax[1].errorbar(t2.plot_date, tbl_bin['RV'] - model_bin, yerr=tbl_bin['ERROR_RV'], linestyle="None", fmt='o',
               alpha = 0.5, capsize = 2, color = 'black')

ax[1].plot(Time(time_plot, format = 'mjd').plot_date,np.zeros(len(time_plot)),'r:')
ax[1].set(xlabel = 'Date', ylabel = 'Residuals [km/s]')
plt.tight_layout()
plt.savefig(object+'.png')
plt.show()

