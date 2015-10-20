#version 8/19/15
from importer import *
from datamanage import *
#ROI wrappers


############################################
# Runs RSA in ROI 
############################################
def roiRSA_1Ss(ds, roi_mask_nii_path, target_dsm, partial_dsm=None, control_dsms=None, cmetric='pearson'):
    '''

    Executes RSA on ROI with target_dm

    ds = pymvpa dataset
    roi_mask_nii_path = path to nifti of roi mask
    target_dsm = primary DM for analysis
    partial_dsm = DM to control for in a partial correlation
    control_dsms = list of DMs to control for in a multiple regression
    cmetric = comparison metric between target dm and neural dm
    '''

    if partial_dsm != None and control_dsms != None: raise NameError('Only set partial_dsm (partial model control) OR control_dsms (multiple regression model controls)')

    data_m = mask_dset(ds, roi_mask_nii_path)
    print('Dataset masked to shape: %s' % (str(data_m.shape)))
 
    print('Beginning roiSxS analysis...')
    ds = mean_group_sample(['targets'])(data_m)
    if partial_dsm == None and control_dsms == None: tdcm = rsa_rymvpa.TargetDissimilarityCorrelationMeasure_Partial(squareform(target_dsm), comparison_metric=cmetric)
    elif partial_dsm != None and control_dsms == None: tdcm = rsa_rymvpa.TargetDissimilarityCorrelationMeasure_Partial(squareform(target_dsm), comparison_metric=cmetric, partial_dsm = squareform(partial_dsm))
    elif partial_dsm == None and control_dsms != None: tdcm = rsa_rymvpa.TargetDissimilarityCorrelationMeasure_Regression(squareform(target_dsm), comparison_metric=cmetric, control_dsms = [squareform(dm) for dm in control_dsms])

    res = tdcm(ds)

    if partial_dsm == None and control_dsms == None:
        return 1-res.samples[1],np.arctanh(res.samples[0])
    elif partial_dsm != None and control_dsms == None:
        return np.arctanh(res.samples[0])
    elif partial_dsm == None and control_dsms != None:
        return res.samples[0]

#############################################
# Runs RSA in ROI per subject
#############################################

def roiRSA_nSs(data, roi_mask_nii_path, target_dsm, partial_dsm=None, control_dsms=None, cmetric='pearson', h5 = 0, h5out = 'roiRSA_nSs.hdf5'):
    '''

    Executes RSA in ROI per subject in datadict 

    data: dictionary of pymvpa dsets per subj, indices being subjIDs
    roi_mask_nii_path = path to nifti of roi mask
    target_dsm = primary DM for analysis
    partial_dsm = DM to control for in analysis, optional
    control_dsms = list of DMs to control for in a multiple regression
    cmetric = comparison metric between target dm and neural dm
    h5: 1 if want h5 per subj 
    h5out: h outfilename suffix
    '''

    print('roiRSA initiated with...\n Ss: %s\nroi_mask: %s\nh5: %s\nh5out: %s' % (data.keys(),roi_mask_nii_path,h5,h5out))

    ### roiRSA per subject ###
    rsar={} #dictionary to hold reuslts per subj
    print('Beginning group level roi analysis on %s Ss...' % (len(data)))

    for subjid,ds in data.iteritems():
        print('\Running roiRSA for subject %s' % (subjid))
        subj_data = roiRSA_1Ss(ds,roi_mask_nii_path,target_dsm,partial_dsm=partial_dsm,control_dsms=control_dsms,cmetric=cmetric)
        rsar[subjid] = subj_data
    print rsar
    res = scipy.stats.ttest_1samp([s[0] for s in rsar.values()],0)
    print('roi group level results: %s' % (str(res)))

    if h5==1:
        h5save(h5out,[res,rsar],compression=9)
        return [res,rsar] 
    else: return [res,rsar]



#############################################
# Runs SampleBySampleSimilarityCorrelation in ROI
#############################################

def roiSxS_1Ss(ds, targs_comps, sample_covariable, roi_mask_nii_path):
    '''

    Executes ROI SampleBySampleSimilarityCorrelation, returns corr coef (and optional p value)

    
    data: pymvpa dset
    targs_comps: dict of trial by trial targets (keys) and their comparison targets (values) - **assumes non-interest targets omitted***
    sample_covariable:  Name of the variable (sample attribute) with a value for each sample. The distance of each sample with the comparison_sample will be correlated with this variable.
    roi_mask_nii_path: Nifti file location of binary mask for ROI
    
    '''    
   
    data_m = mask_dset(ds, roi_mask_nii_path)
    print('Dataset masked to shape: %s' % (str(data_m.shape)))
 
    print('Beginning roiSxS analysis...')
    SxS = rsa_rymvpa.SampleBySampleSimilarityCorrelation(targs_comps,sample_covariable)
    sxsr = SxS(data_m)
    #change slmap to right format
    sxsr.samples[0],sxsr.samples[1]=np.arctanh(sxsr.samples[0]),1-sxsr.samples[1]

    return sxsr    


#############################################
# Runs SampleBySampleSimilarityCorrelation in ROI per Subject
#############################################

def roiSxS_nSs(data, targs_comps, sample_covariable, roi_mask_nii_path, h5 = 0, h5out = 'roiSxS_nSs.hdf5'):
    '''

    Executes searchlight SampleBySampleSimilarityCorrelation, returns corr coef (and optional p value) per voxel

    ***assumes anything not in targs_comps is omitted***

    data: dictionary of pymvpa dsets per subj, indices being subjIDs
    targs_comps: dict of trial by trial targets (keys) and their comparison targets (values) - **assumes non-interest targets omitted***
    sample_covariable:  Name of the variable (sample attribute) with a value for each sample. The distance of each sample with the comparison_sample will be correlated with this variable.
    h5: 1 if want h5 per subj 
    h5out: h outfilename suffix
    '''        
    
    print('roiSxS initiated with...\n Ss: %s\ncomparison sample: %s\nsample covariable: %s\nroi_mask: %s\nh5: %s\nh5out: %s' % (data.keys(),targs_comps,sample_covariable,roi_mask_nii_path,h5,h5out))

    ### slSxS per subject ###
    sxsr={} #dictionary to hold reuslts per subj
    print('Beginning group level roi analysis on %s Ss...' % (len(data)))
    for subjid,ds in data.iteritems():
        print('\Running roiSxS for subject %s' % (subjid))
        subj_data = roiSxS_1Ss(ds,targs_comps,sample_covariable,roi_mask_nii_path)
        sxsr[subjid] = subj_data
    print('roiSxS complete for all subjects')
    res = scipy.stats.ttest_1samp([s.samples[0][0] for s in sxsr.values()],0)
    print('roi group level results: %s' % (str(res)))

    if h5==1:
        h5save(h5out,[res,sxsr],compression=9)
        return [res,sxsr] 
    else: return [res,sxsr]


##############################################
# BDSM ROI
###############################################

def roiBDSM_xSs(data, xSs_behav, targ_comp, roi_mask_nii_path, h5 = 0,h5out = 'bdsm_roi.hdf5'):
    '''
    
    Returns correlation of subject-level behav sim with subject-level neural sim between two targs

    data: dictionary of pymvpa dsets per subj, indices being subjIDs
    xSs_behav: Dictionary of behavioral value between subjects to be
               correlated with intrasubject neural similarity (subjects are keys)
    targ_comp: List of targets whose similarity is correlated with xSs_behav
    roi_mask_nii_path: Nifti file location of binary  mask for ROI
    h5: 1 saves hdf5 of output as well 
    h5out: hdf5 outfilename
    
    '''   

    print('xSs BDSM initiated with...\n Ss: %s \n targ_comp: %s\nroi_mask: %s\nh5: %s\nh5out: %s' % (data.keys(),targ_comp,roi_mask_nii_path,h5,h5out))

    for i in data:
        data[i] = mean_group_sample(['targets'])(data[i]) 
    print('Dataset targets averaged with shapes:',[ds.shape for ds in data.values()])

    group_data = None
    for s in data.keys():
         ds = data[s]
         ds.sa['chunks'] = [s]*len(ds)
         if group_data is None: group_data = ds
         else: group_data.append(ds)
    print('Group dataset ready including Ss: %s\nBeginning slBDSM:' % (np.unique(group_data.chunks)))

    group_data_m = mask_dset(group_data,roi_mask_nii_path)
    print('Group dataset masked, to size: %s' % (str(group_data_m.shape)))

    bdsm = rsa_rymvpa.xss_BehavioralDissimilarity(xSs_behav,targ_comp)
    roi_bdsm = bdsm(group_data_m)
    bdsmr = roi_bdsm.samples[0][0]
    print('Analysis complete with r: %s' % (str(bdsmr)))

    if h5 == 1:
        h5save(h5out,bdsmr,compression=9)
        return bdsmr
    else: return bdsmr


###############################################
# BDSM ROI double
###############################################

def roiBDSM_xSs_d(data,xSs_behav1,targ_comp1,xSs_behav2,targ_comp2,roi_mask_nii_path,h5=0,h5out='bdsm_xSs.hdf5'):
    '''
    
    Returns correlation of subject-level behav sim with subject-level neural sim between two targs

    data: dictionary of pymvpa dsets per subj, indices being subjIDs
    xSs_behav: Dictionary of behavioral value between subjects to be
               correlated with intrasubject neural similarity (subjects are keys)
    targ_comp: List of targets whose similarity is correlated with xSs_behav
    roi_mask_nii_path: path to nifti mask file for ROI
    h5: 1 saves hdf5 of output as well 
    h5out: hdf5 outfilename
    
    '''   

    print('xSs BDSM initiated with...\n Ss: %s \n targ_comp1: %s\n targ_comp2: %s\n mask_roi: %s\nh5: %s\nh5out: %s' % (data.keys(),targ_comp1,targ_comp2,roi_mask_nii_path,h5,h5out))

    for i in data:
        data[i] = mean_group_sample(['targets'])(data[i]) 
    print('Dataset targets averaged with shapes:',[ds.shape for ds in data.values()])

    group_data = None
    for s in data.keys():
         ds = data[s]
         ds.sa['chunks'] = [s]*len(ds)
         if group_data is None: group_data = ds
         else: group_data.append(ds)
    print('Group dataset ready including Ss: %s\nBeginning slBDSM:' % (np.unique(group_data.chunks)))

    group_data_m = mask_dset(group_data,roi_mask_nii_path)
    print('Group dataset masked, to size: %s' % (str(group_data_m.shape)))

    bdsm = rsa_rymvpa.xss_BehavioralDissimilarity_double(xSs_behav1,targ_comp1,xSs_behav2,targ_comp2)
    roi_bdsm = bdsm(group_data_m)
    bdsmr = roi_bdsm.samples[0][0]
    print('Analysis complete with r: %s' % (str(bdsmr)))

    if h5 == 1:
        h5save(h5out,bdsmr,compression=9)
        return bdsmr
    else: return bdsmr


