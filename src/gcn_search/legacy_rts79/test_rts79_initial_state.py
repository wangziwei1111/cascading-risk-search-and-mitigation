from __future__ import annotations

import numpy as np

from rts79_cascade import (
    Rts79InitialConfig,
    check_paper_case_points,
    line_label_to_index_1based,
    load_rts79_case,
    run_initial_dcopf,
    run_post_outage_dcopf,
    run_protection_cascade_dcpf,
    redispatch_minimize_load_shed,
    search_all_n2_cascade_paths,
    search_n2_paths_for_load_scenarios,
    simulate_cascade_path,
    run_sequential_initial_outages_dcpf,
)


def test_rts79_base_case_matches_paper_size() -> None:
    case = load_rts79_case()
    assert case["bus"].shape[0] == 24
    assert case["branch"].shape[0] == 38
    assert case["gen"].shape[0] == 33
    assert np.isclose(case["bus"][:, 2].sum(), 2850.0)
    assert np.isclose(case["gen"][:, 8].sum(), 3405.0)


def test_initial_dcopf_converges_and_respects_branch_limits() -> None:
    state = run_initial_dcopf(
        Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        )
    )
    assert np.isclose(state.bus_table["P_D_MW"].sum(), 3135.0)
    assert np.isclose(state.generator_table["P_G_MW"].sum(), 3135.0)
    assert state.branch_table["loading_ratio"].max() <= 1.0 + 1e-7
    assert state.branch_table["line_label"].tolist()[0] == "L01"
    assert state.bus_table["bus_label"].tolist()[0] == "B01"


def test_post_outage_dcopf_opens_requested_line_and_reports_overloads() -> None:
    state = run_post_outage_dcopf(
        ["L10"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
    )
    l10_row = state.branch_table.loc[state.branch_table["line_label"] == "L10"].iloc[0]
    assert l10_row["status"] == 0
    assert line_label_to_index_1based("L10") == 10
    assert state.branch_table.loc[state.branch_table["status"] == 1, "loading_ratio"].max() <= 1.0 + 1e-7
    assert state.overloaded_lines == ()


def test_protection_cascade_dcpf_opens_requested_line_and_stabilizes() -> None:
    state = run_protection_cascade_dcpf(
        ["L10"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
    )
    l10_row = state.final_branch_table.loc[state.final_branch_table["line_label"] == "L10"].iloc[0]
    online = state.final_branch_table["status"] == 1
    assert state.converged
    assert l10_row["status"] == 0
    assert state.round_table.iloc[-1]["num_newly_tripped"] == 0
    assert state.final_branch_table.loc[online, "loading_ratio"].max() <= 1.0 + 1e-7


def test_sequential_n2_outages_apply_in_order_and_stabilize() -> None:
    state = run_sequential_initial_outages_dcpf(
        ["L10", "L07"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
    )
    online = state.final_branch_table["status"] == 1
    assert state.converged
    assert state.initial_outage_sequence == ("L10", "L07")
    assert {"L10", "L07"}.issubset(set(state.final_outage_labels))
    assert state.event_table["event"].drop_duplicates().tolist() == [1, 2]
    assert state.event_table.iloc[-1]["num_newly_tripped"] == 0
    assert state.final_branch_table.loc[online, "loading_ratio"].max() <= 1.0 + 1e-7


def test_sequential_n2_outages_shed_load_for_l10_l05_island() -> None:
    state = run_sequential_initial_outages_dcpf(
        ["L10", "L05"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        )
    )
    online = state.final_branch_table["status"] == 1
    assert state.converged
    assert {"L10", "L05"}.issubset(set(state.final_outage_labels))
    assert state.total_load_shed_mw > 0.0
    assert "B06" in set(state.bus_shed_table["bus_label"])
    assert state.final_branch_table.loc[online, "loading_ratio"].max() <= 1.0 + 1e-7


def test_redispatch_minimizes_additional_shed_and_respects_line_limits() -> None:
    sequence_state = run_sequential_initial_outages_dcpf(
        ["L10", "L05"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
    )
    redispatch_state = redispatch_minimize_load_shed(sequence_state.case)
    online = redispatch_state.final_branch_table["status"] == 1
    assert redispatch_state.success
    assert redispatch_state.total_load_shed_mw <= 1e-7
    assert redispatch_state.final_branch_table.loc[online, "loading_ratio"].max() <= 1.0 + 1e-7


def test_simulate_cascade_path_returns_complete_critical_result() -> None:
    result = simulate_cascade_path(
        ["L10", "L05"],
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
    )
    assert result.converged
    assert result.critical
    assert result.total_load_shed_mw > 0.0
    assert result.redispatch_load_shed_mw <= 1e-7
    assert result.final_max_loading_ratio <= 1.0 + 1e-7


def test_n2_search_preview_records_ordered_paths() -> None:
    result = search_all_n2_cascade_paths(
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
        max_paths=5,
    )
    assert result.num_paths == 5
    assert result.summary_table["path"].tolist() == ["L01->L02", "L01->L03", "L01->L04", "L01->L05", "L01->L06"]
    assert {"path", "critical", "total_load_shed_mw", "final_outage_labels"}.issubset(result.summary_table.columns)


def test_multi_scenario_search_records_seeded_load_scenarios() -> None:
    result = search_n2_paths_for_load_scenarios(
        seeds=[7, 8],
        load_scale=1.1,
        load_random_low=0.9,
        load_random_high=1.1,
        max_paths_per_scenario=3,
    )
    assert result.num_scenarios == 2
    assert result.path_result_table.shape[0] == 6
    assert result.scenario_summary_table["seed"].tolist() == [7, 8]
    assert {"path", "path_frequency", "mean_total_load_shed_mw"}.issubset(
        result.critical_path_frequency_table.columns
    )


def test_check_paper_case_points_exports_two_cases() -> None:
    table = check_paper_case_points(
        config=Rts79InitialConfig(
            random_seed=7,
            load_scale=1.1,
            load_random_low=1.0,
            load_random_high=1.0,
        ),
        output_dir="outputs/test_paper_case_check",
    )
    assert table["path"].tolist() == ["L10->L05", "L27->L02"]
    assert "B06" in table.loc[table["path"] == "L10->L05", "island_shed_buses"].iloc[0]
