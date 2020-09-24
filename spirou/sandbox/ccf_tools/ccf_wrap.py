from astropy.table import Table
import numpy as np
import glob
from astropy.io import fits
from tqdm import tqdm
from apero.recipes.spirou import cal_ccf_spirou
import os
from sanitize import *
import sys

"""
This code is only used at UdeM but could be used to replicate the batches of CCFs at other sites.

You can get inspired by this code to construct a similar batch script.
"""

# you absolutely need to modify these paths
path_to_masks = '/spirou/drs/apero-drs/apero/data/spirou/ccf/'
path = '/spirou/cfht_nights/cfht_july1/reduced/20??-??-??/*o_pp_e2dsff_tcorr_AB.fits'

# fetch the latest table with the table of requests
os.system('rm ccf_wrap.tbl')
os.system('wget https://raw.githubusercontent.com/njcuk9999/apero-utils/master/spirou/sandbox/ccf_tools/ccf_wrap.tbl')

step = 0.1
width = 60.0
prob_bad = 1e-4

all_done = False

while all_done == False:
    # that's batches to come
    tbl = Table.read('ccf_wrap.tbl',format = 'csv')
    objects = np.array(tbl['OBJECT'])
    masks = np.array(tbl['MASK'])
    do_sanitize_all = tbl['SANITIZE'] == 'True'

    todo  = np.zeros_like(tbl,dtype = bool)
    tar_names = []
    for i in range(len(tbl)):
        if do_sanitize_all[i]:
            suffix = 'sanitize_'
        else:
            suffix = ''

        tar_name = 'all_ccfs/{0}_{1}mask_{2}_ccf.tar'.format(objects[i],suffix,masks[i].split('.')[0])
        tar_names = np.append(tar_names,tar_name)

        if  os.path.isfile(tar_names[i]):
            print('We already have {0} in our folders...'.format(tar_name))
        else:
            todo[i] = True

        if not os.path.isfile(path_to_masks + tbl['MASK'][i]):
            print('We do not have a file named {0}'.format(path_to_masks + tbl['MASK'][i]))
            todo[i] = False

    if True not in todo:
        all_done = True
    else:
        # We create a trimmed-down version of the list with only files to be done
        tar_names = tar_names[todo]
        tbl = tbl[todo]
        objects = np.array(tbl['OBJECT'])
        masks = np.array(tbl['MASK'])
        do_sanitize_all = tbl['SANITIZE'] == 'True'


        object = objects[0]
        mask = masks[0]
        do_sanitize = do_sanitize_all[0]
        tar_name = tar_names[0]



        if os.path.isfile(tar_name):
            print('File {0} exists, we skip'.format(tar_name))
            continue

        nights = []
        files = []

        sample_files = glob.glob(path)

        print('Scanning all files with the search string : \n')
        print('\t {0}\n'.format(path))

        for file in tqdm(sample_files):
            hdr = fits.getheader(file)
            if hdr['OBJECT'] == object:

                if do_sanitize:
                    blaze_file = file.split('reduced')[0]+'calibDB/'+hdr['CDBBLAZE']
                    model_s1d_file = file.split('reduced/')[0]+'reduced/other/Template_s1d_{0}_sc1d_v_file_AB.fits'.format(object)
                    #file = 'sani'.join(file.split('tcorr'))
                    sanitize([file], blaze_file, model_s1d_file, prob_bad = prob_bad, force = False,doplot = [-1])
                    file = 'sani'.join(file.split('tcorr'))

                files = np.append(files,file.split('/')[-1])
                nights = np.append(nights,file.split('/')[-2])

        print('We have {0} files for {1}'.format(len(files),object))

        outnames = []
        for i in range(len(files)):
            print('\n\tFile {0}/{1}\n'.format(i,len(files)))

            outname = '/spirou/cfht_nights/cfht_july1/reduced/'+nights[i]+'/'+files[i].split('.')[0]+'_ccf_'+mask.split('.')[0].lower()+'_AB.fits'

            if i ==0:
                tmp = cal_ccf_spirou.main(nights[i], files[i], mask=mask, rv=0.0, step=step, width=300.0)
                tbl = fits.getdata(outname)
                ccf = np.array(tbl['COMBINED'])
                # remove trend of CCF for large berv range
                ccf -= np.polyval(np.polyfit(tbl['RV'],ccf,1),   tbl['RV'])
                rv =  np.round(tbl['RV'][np.argmin(ccf)],1)
                print('\tRV = {0}km/s'.format(rv))

            tmp = cal_ccf_spirou.main(nights[i], files[i], mask=mask, rv=rv, step=step, width=30.0)

            outnames = np.append(outnames,outname)


        for i in range(len(outnames)):
            os.system('cp '+outnames[i]+' .')
            outnames[i] = outnames[i].split('/')[-1]
        os.system('tar -cvf {0} {1}'.format(tar_name,' '.join(outnames)))

        for i in range(len(outnames)):
            os.system('rm '+outnames[i])

        tar_files = glob.glob('all_ccfs/*.tar')
        sz = np.zeros(len(tar_files),dtype = '<U99')
        for i in range(len(tar_files)):
            sz[i] =  '['+str(np.round((os.stat(tar_files[i]).st_size)/1e6,1))+' Mb]'
            tar_files[i] = tar_files[i].split('/')[-1]

        f = open('all_ccfs/download_ccf.script','w')

        for i in range(len(tar_files)):
            f.write('wget http://www.astro.umontreal.ca/~artigau/all_ccfs/{0}\n'.format(tar_files[i]))

        for i in range(len(tar_files)):
            obj = tar_files[i].split('_mask_')[0]
            f.write('mkdir {0}\n'.format(obj))
            f.write('mv {0} {1}\n'.format(tar_files[i],obj))
            f.write('cd {0}\n'.format(obj))
            f.write('tar -xvf {0}\n'.format(tar_files[i]))
            f.write('rm  {0}\n'.format(tar_files[i]))
            f.write('cd ..\n')
        f.close()

        os.system('rsync -av -e "ssh  -oPort=5822" all_ccfs artigau@venus.astro.umontreal.ca:/home/artigau/www')

        tar_files = glob.glob('all_ccfs/*.tar')
        sz = np.zeros(len(tar_files),dtype = '<U99')
        for i in range(len(tar_files)):
            sz[i] =  '['+str(np.round((os.stat(tar_files[i]).st_size)/1e6,1))+' Mb]'
            tar_files[i] = tar_files[i].split('/')[-1]

        f = open('all_ccfs/download_ccf.script','w')

        for i in range(len(tar_files)):
            f.write('wget http://www.astro.umontreal.ca/~artigau/all_ccfs/{0}\n'.format(tar_files[i]))

        for i in range(len(tar_files)):
            obj = tar_files[i].split('_mask_')[0]
            f.write('mkdir {0}\n'.format(obj))
            f.write('mv {0} {1}\n'.format(tar_files[i],obj))
            f.write('cd {0}\n'.format(obj))
            f.write('tar -xvf {0}\n'.format(tar_files[i]))
            f.write('rm  {0}\n'.format(tar_files[i]))
            f.write('cd ..\n')
        f.close()

f = open('email','w')
f.write('This is an automated email to list all CCF compilations done to date.\n')
f.write('Copy-paste the commands below in a terminal to get all CCF files. To \n')
f.write('perform the analysis of these files, use the code provided here :\n')
f.write('\n')
f.write('https://github.com/njcuk9999/apero-utils/tree/master/spirou/sandbox/ccf_tools\n')
f.write('\n')
f.write('Lines to copy-paste, it is best to run this script in the folder used \n')
f.write('for your CCF analysis. The scirpt will create per-object folders and  \n')
f.write('distribute files in these folders\n')
f.write('\n')
f.write('\t wget http://www.astro.umontreal.ca/~artigau/all_ccfs/download_ccf.script\n')
f.write('\t chmod a+x download_ccf.script\n')
f.write('\t ./download_ccf.script\n')
f.write('\t rm download_ccf.script\n')
f.write('\n')
f.write('Files that will be downloaded and extracted from tar\n')

for i in range(len(tar_files)):
    f.write('\t{0} {1}\n'.format(tar_files[i],sz[i]))

f.write('\n')
f.write('May the CCF be with you,\n')
f.write('The DRS team')
f.close()

emails = ['cadieux','vandal','doyon','artigau','andres.carmona@univ-grenoble-alpes.fr']
for email in emails:
    os.system('cat email | mail -s "Automated links to compiled CCFs" {0}'.format(email))
