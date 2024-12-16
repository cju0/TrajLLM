from scipy.stats import lognorm, expon, gamma, powerlaw, weibull_min
import numpy as np

def gen_time_duration_overall(factors, confidence=0.95):
    '''Using log-normal distribution to generate a random time duration in minutes 
    based on OVERALL checkin time duration distribution'''

    shape, loc, scale = factors

    lower_bound = lognorm.ppf((1 - confidence) / 2, shape, loc=loc, scale=scale)
    upper_bound = lognorm.ppf((1 + confidence) / 2, shape, loc=loc, scale=scale)

    while True:
        sample = lognorm.rvs(shape, loc=loc, scale=scale)
        if lower_bound <= sample <= upper_bound:
            return sample

def gen_time_duration_cate(kde_obj):
    '''Generate a random time duration with a specific location category based on generated distributions'''

    sample_min = np.min(kde_obj.dataset)
    sample_max = np.max(kde_obj.dataset)
    
    while True:
        random_duration = kde_obj.resample(1).item()
        if sample_min <= random_duration <= sample_max:
            return random_duration

def gen_time_duration_bestfit(fitted_params, confidence=0.95):

    if not fitted_params:
        raise ValueError(f"No fitted parameters found for given category")

    method = fitted_params['method']
    params = fitted_params['parameters']

    # Infinite loop to ensure sample within bounds
    if method in ['Gamma', 'Weibull', 'LogNormal', 'Exponential']:
        if method == 'Gamma':
            shape, loc, scale = params
            lower_bound = gamma.ppf((1 - confidence) / 2, shape, loc=loc, scale=scale)
            upper_bound = gamma.ppf((1 + confidence) / 2, shape, loc=loc, scale=scale)
        elif method == 'Weibull':
            shape, loc, scale = params
            lower_bound = weibull_min.ppf((1 - confidence) / 2, shape, loc=loc, scale=scale)
            upper_bound = weibull_min.ppf((1 + confidence) / 2, shape, loc=loc, scale=scale)
        elif method == 'LogNormal':
            shape, loc, scale = params
            lower_bound = lognorm.ppf((1 - confidence) / 2, shape, loc=loc, scale=scale)
            upper_bound = lognorm.ppf((1 + confidence) / 2, shape, loc=loc, scale=scale)
        elif method == 'Exponential':
            loc, scale = params
            lower_bound = expon.ppf((1 - confidence) / 2, loc=loc, scale=scale)
            upper_bound = expon.ppf((1 + confidence) / 2, loc=loc, scale=scale)

        # Generate samples within bounds
        while True:
            if method == 'Gamma':
                sample = gamma.rvs(shape, loc, scale)
            elif method == 'Weibull':
                sample = weibull_min.rvs(shape, loc, scale)
            elif method == 'LogNormal':
                sample = lognorm.rvs(shape, loc, scale)
            elif method == 'Exponential':
                sample = expon.rvs(loc, scale)

            if lower_bound <= sample <= upper_bound:
                return sample

    elif method == 'GMM':
        weights, means, covariances = params

        # Estimate bounds for the GMM based on individual components
        min_bound = np.min([np.min(mean - 3 * np.sqrt(np.diag(cov))) for mean, cov in zip(means, covariances)])
        max_bound = np.max([np.max(mean + 3 * np.sqrt(np.diag(cov))) for mean, cov in zip(means, covariances)])

        while True:
            # Step 1: Randomly select a component based on weights
            component = np.random.choice(len(weights), p=weights)

            # Step 2: Sample from the chosen Gaussian component
            mean = means[component].flatten()  # Flatten to 1D if necessary
            covariance = covariances[component]
            sample = np.random.multivariate_normal(mean, covariance)

            if min_bound <= sample[0] <= max_bound:
                return sample[0]

    elif method == 'KDE':
        kde = params
        lower_bound, upper_bound = np.percentile(kde.dataset, [(1 - confidence) * 100 / 2, (1 + confidence) * 100 / 2])

        while True:
            sample = kde.resample(1)[0][0]  # 从KDE中生成一个样本
            if lower_bound <= sample <= upper_bound:
                return sample

    else:
        raise ValueError(f"Unsupported distribution method: {method}")
