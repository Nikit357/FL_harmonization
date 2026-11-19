# Pilot report (gate G3)

Harmonization runs: 85 (3 failed: grad_cap150_l1.0_r1 × 05_combat, v1_C_f1_test × 36_explobatch, v1_C_f1_train × 36_explobatch)

Projected wall time with 8 workers (linear-in-n scaling, a lower bound for the S0 training folds):
- gradient: 5.6 h
- v1: 36.7 h

Methods slower than 30 min on the 1,869-sample training part (decision D8 fallback candidates): Shambhala-2, HarmonizR

Metric jobs: 82; status {'ok': 82}; median 4.0 min per job

Covariate arms: see pilot_nocov_check.tsv (status and method messages).
