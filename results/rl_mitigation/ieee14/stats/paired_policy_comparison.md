# IEEE14 Paired Policy Comparison

All comparisons are paired by identical test scenario_id. Lower values are better for negative_return, num_generations, num_line_outages, and load_shed_MW.

- ppo_do_nothing_init vs do_nothing on negative_return: mean_diff=0.0050, CI=[0.0010, 0.0090], improved_ratio=0.000, worse_ratio=0.050 (stable direction).
- ppo_do_nothing_init vs do_nothing on num_generations: mean_diff=0.0000, CI=[0.0000, 0.0000], improved_ratio=0.000, worse_ratio=0.000 (stable direction).
- ppo_do_nothing_init vs do_nothing on num_line_outages: mean_diff=0.0500, CI=[0.0100, 0.0902], improved_ratio=0.000, worse_ratio=0.050 (stable direction).
- ppo_do_nothing_init vs do_nothing on load_shed_MW: mean_diff=0.0000, CI=[0.0000, 0.0000], improved_ratio=0.000, worse_ratio=0.000 (stable direction).
- ppo_oracle_bc_init vs do_nothing on negative_return: mean_diff=24.9149, CI=[15.9570, 34.3759], improved_ratio=0.590, worse_ratio=0.410 (stable direction).
- ppo_oracle_bc_init vs do_nothing on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], improved_ratio=0.200, worse_ratio=0.000 (stable direction).
- ppo_oracle_bc_init vs do_nothing on num_line_outages: mean_diff=-2.0100, CI=[-2.6202, -1.4000], improved_ratio=0.570, worse_ratio=0.400 (stable direction).
- ppo_oracle_bc_init vs do_nothing on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], improved_ratio=0.420, worse_ratio=0.000 (stable direction).
- one_step_oracle vs do_nothing on negative_return: mean_diff=-8.1251, CI=[-13.2694, -4.2768], improved_ratio=0.600, worse_ratio=0.000 (stable direction).
- one_step_oracle vs do_nothing on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], improved_ratio=0.200, worse_ratio=0.000 (stable direction).
- one_step_oracle vs do_nothing on num_line_outages: mean_diff=-2.4100, CI=[-2.9500, -1.8798], improved_ratio=0.570, worse_ratio=0.000 (stable direction).
- one_step_oracle vs do_nothing on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], improved_ratio=0.420, worse_ratio=0.000 (stable direction).
- ppo_oracle_bc_init vs ppo_do_nothing_init on negative_return: mean_diff=24.9099, CI=[15.9480, 34.3747], improved_ratio=0.590, worse_ratio=0.370 (stable direction).
- ppo_oracle_bc_init vs ppo_do_nothing_init on num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], improved_ratio=0.200, worse_ratio=0.000 (stable direction).
- ppo_oracle_bc_init vs ppo_do_nothing_init on num_line_outages: mean_diff=-2.0600, CI=[-2.6700, -1.4500], improved_ratio=0.570, worse_ratio=0.360 (stable direction).
- ppo_oracle_bc_init vs ppo_do_nothing_init on load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], improved_ratio=0.420, worse_ratio=0.000 (stable direction).