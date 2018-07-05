/**
 * Model for estimating a reasonable distribution over matchup percentages.
 */
data {
    int<lower=0> n_matchups;
    int<lower=0, upper=n_matchups> n_modeled;
    int w[n_matchups];
    int n[n_matchups];
}
parameters {
    real<lower=0, upper=1000> alpha;
    vector<lower=0, upper=1>[n_modeled] mwp;
}
model {
    for (i in 1:n_modeled) {
        mwp[i] ~ beta(alpha, alpha);
    }
    w[1:n_modeled] ~ binomial(n[1:n_modeled], mwp);
    w[(n_modeled+1):n_matchups] ~ beta_binomial(n[(n_modeled+1):n_matchups], alpha, alpha);
}
