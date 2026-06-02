# IEEE14 Paired Policy Comparison

All comparisons are paired by identical test scenario_id. Lower values are better for negative_return, num_generations, num_line_outages, and load_shed_MW.

- ppo_do_nothing_init vs do_nothing on negative_return: mean_diff=0.0050, CI=[0.0010, 0.0090], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.050 (worse).
- ppo_do_nothing_init vs do_nothing on num_generations: mean_diff=0.0000, CI=[0.0000, 0.0000], direction=no_clear_difference, improved_ratio=0.000, worse_ratio=0.000 (indistinguishable).
- ppo_do_nothing_init vs do_nothing on num_line_outages: mean_diff=0.0500, CI=[0.0100, 0.0902], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.050 (worse).
- ppo_do_nothing_init vs do_nothing on load_shed_MW: mean_diff=0.0000, CI=[0.0000, 0.0000], direction=no_clear_difference, improved_ratio=0.000, worse_ratio=0.000 (indistinguishable).
- ppo_oracle_bc_init vs do_nothing on negative_return: mean_diff=24.9149, CI=[15.9570, 34.3759], direction=policy_a_worse, improved_ratio=0.590, worse_ratio=0.410 (worse).
- ppo_oracle_bc_init vs do_nothing on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], direction=policy_a_better, improved_ratio=0.200, worse_ratio=0.000 (improved).
- ppo_oracle_bc_init vs do_nothing on num_line_outages: mean_diff=-2.0100, CI=[-2.6202, -1.4000], direction=policy_a_better, improved_ratio=0.570, worse_ratio=0.400 (improved).
- ppo_oracle_bc_init vs do_nothing on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], direction=policy_a_better, improved_ratio=0.420, worse_ratio=0.000 (improved).
- oracle_bc_positive_only vs do_nothing on negative_return: mean_diff=24.9149, CI=[15.9570, 34.3759], direction=policy_a_worse, improved_ratio=0.590, worse_ratio=0.410 (worse).
- oracle_bc_positive_only vs do_nothing on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], direction=policy_a_better, improved_ratio=0.200, worse_ratio=0.000 (improved).
- oracle_bc_positive_only vs do_nothing on num_line_outages: mean_diff=-2.0100, CI=[-2.6202, -1.4000], direction=policy_a_better, improved_ratio=0.570, worse_ratio=0.400 (improved).
- oracle_bc_positive_only vs do_nothing on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], direction=policy_a_better, improved_ratio=0.420, worse_ratio=0.000 (improved).
- oracle_bc_full vs do_nothing on negative_return: mean_diff=-1.5654, CI=[-2.1132, -1.0409], direction=policy_a_better, improved_ratio=0.280, worse_ratio=0.000 (improved).
- oracle_bc_full vs do_nothing on num_generations: mean_diff=-0.0100, CI=[-0.0400, 0.0000], direction=no_clear_difference, improved_ratio=0.010, worse_ratio=0.000 (indistinguishable).
- oracle_bc_full vs do_nothing on num_line_outages: mean_diff=-1.3100, CI=[-1.7905, -0.8700], direction=policy_a_better, improved_ratio=0.270, worse_ratio=0.000 (improved).
- oracle_bc_full vs do_nothing on load_shed_MW: mean_diff=-13.0164, CI=[-18.5435, -7.8720], direction=policy_a_better, improved_ratio=0.250, worse_ratio=0.000 (improved).
- safe_oracle_bc_full vs do_nothing on negative_return: mean_diff=-0.8946, CI=[-1.3881, -0.4608], direction=policy_a_better, improved_ratio=0.130, worse_ratio=0.000 (improved).
- safe_oracle_bc_full vs do_nothing on num_generations: mean_diff=0.0000, CI=[0.0000, 0.0000], direction=no_clear_difference, improved_ratio=0.000, worse_ratio=0.000 (indistinguishable).
- safe_oracle_bc_full vs do_nothing on num_line_outages: mean_diff=-0.7800, CI=[-1.2203, -0.3898], direction=policy_a_better, improved_ratio=0.130, worse_ratio=0.000 (improved).
- safe_oracle_bc_full vs do_nothing on load_shed_MW: mean_diff=-9.5323, CI=[-14.9104, -4.5491], direction=policy_a_better, improved_ratio=0.130, worse_ratio=0.000 (improved).
- one_step_oracle vs do_nothing on negative_return: mean_diff=-8.1251, CI=[-13.2694, -4.2768], direction=policy_a_better, improved_ratio=0.600, worse_ratio=0.000 (improved).
- one_step_oracle vs do_nothing on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], direction=policy_a_better, improved_ratio=0.200, worse_ratio=0.000 (improved).
- one_step_oracle vs do_nothing on num_line_outages: mean_diff=-2.4100, CI=[-2.9500, -1.8798], direction=policy_a_better, improved_ratio=0.570, worse_ratio=0.000 (improved).
- one_step_oracle vs do_nothing on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], direction=policy_a_better, improved_ratio=0.420, worse_ratio=0.000 (improved).
- ppo_oracle_bc_init vs ppo_do_nothing_init on negative_return: mean_diff=24.9099, CI=[15.9480, 34.3747], direction=policy_a_worse, improved_ratio=0.590, worse_ratio=0.370 (worse).
- ppo_oracle_bc_init vs ppo_do_nothing_init on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], direction=policy_a_better, improved_ratio=0.200, worse_ratio=0.000 (improved).
- ppo_oracle_bc_init vs ppo_do_nothing_init on num_line_outages: mean_diff=-2.0600, CI=[-2.6700, -1.4500], direction=policy_a_better, improved_ratio=0.570, worse_ratio=0.360 (improved).
- ppo_oracle_bc_init vs ppo_do_nothing_init on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], direction=policy_a_better, improved_ratio=0.420, worse_ratio=0.000 (improved).
- safe_oracle_bc_full vs oracle_bc_full on negative_return: mean_diff=0.6708, CI=[0.3591, 1.0027], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.160 (worse).
- safe_oracle_bc_full vs oracle_bc_full on num_generations: mean_diff=0.0100, CI=[0.0000, 0.0400], direction=no_clear_difference, improved_ratio=0.000, worse_ratio=0.010 (indistinguishable).
- safe_oracle_bc_full vs oracle_bc_full on num_line_outages: mean_diff=0.5300, CI=[0.2798, 0.8100], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.150 (worse).
- safe_oracle_bc_full vs oracle_bc_full on load_shed_MW: mean_diff=3.4840, CI=[1.3550, 5.8989], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.120 (worse).
- oracle_bc_full vs oracle_bc_positive_only on negative_return: mean_diff=-26.4802, CI=[-35.8271, -17.5864], direction=policy_a_better, improved_ratio=0.410, worse_ratio=0.410 (improved).
- oracle_bc_full vs oracle_bc_positive_only on num_generations: mean_diff=0.1900, CI=[0.1200, 0.2700], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.190 (worse).
- oracle_bc_full vs oracle_bc_positive_only on num_line_outages: mean_diff=0.7000, CI=[0.3400, 1.1002], direction=policy_a_worse, improved_ratio=0.400, worse_ratio=0.400 (worse).
- oracle_bc_full vs oracle_bc_positive_only on load_shed_MW: mean_diff=2.4097, CI=[0.9188, 4.4416], direction=policy_a_worse, improved_ratio=0.000, worse_ratio=0.170 (worse).