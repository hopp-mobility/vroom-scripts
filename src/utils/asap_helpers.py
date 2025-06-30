#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import matplotlib.pyplot as plt
import sys
from utils.vroom import solve

# Parse a json-formatted input instance, then apply iterative solving
# strategies to come up with a solution minimizing completion time.


def filter_dominated(solutions):
    indices = range(len(solutions))
    completion_times = []
    costs = []
    to_pop = []

    for i in indices:
        sol = solutions[i]
        completion_times.append(max([r["steps"][-1]["arrival"] for r in sol["routes"]]))
        costs.append(sol["summary"]["cost"])

    for i in indices:
        for j in indices:
            if j == i:
                continue
            if completion_times[j] < completion_times[i] and costs[j] < costs[i]:
                to_pop.append(i)
                break

    for i in reversed(to_pop):
        solutions.pop(i)


def filter_unique(solutions):
    indices = range(len(solutions))
    completion_times = []
    costs = []
    to_pop = []

    for i in indices:
        sol = solutions[i]
        completion_times.append(max([r["steps"][-1]["arrival"] for r in sol["routes"]]))
        costs.append(sol["summary"]["cost"])

    for i in indices:
        for j in range(i + 1, len(solutions)):
            if j in to_pop:
                continue

            if completion_times[j] == completion_times[i] and costs[j] == costs[i]:
                to_pop.append(j)
                break

    for i in reversed(to_pop):
        solutions.pop(i)


def dichotomy(data, cl_args, first_solution):
    init_input = copy.deepcopy(data)
    solutions = []

    if len(first_solution["routes"]) > 0:
        sol = copy.deepcopy(first_solution)
        sol["origin"] = "dichotomy"
        solutions.append(sol)

    end_dates = [r["steps"][-1]["arrival"] for r in first_solution["routes"]]
    earliest = min(end_dates)
    latest = max(end_dates)

    earliest_TW = sys.maxsize

    for vehicle in init_input["vehicles"]:
        if "time_window" in vehicle:
            earliest_TW = min(earliest_TW, vehicle["time_window"][0])
        else:
            vehicle["time_window"] = [0, latest]
            earliest_TW = 0

    if len(first_solution["routes"]) < len(init_input["vehicles"]):
        # There is an unused vehicle in the initial solution so
        # current earliest is meaningless.
        earliest = earliest_TW

    end_candidate = int(round(float(earliest + latest) / 2))
    while (end_candidate != earliest) and (end_candidate != latest):
        # Force end_candidate as new end date for all vehicles.
        current = copy.deepcopy(init_input)

        for v in range(len(current["vehicles"]) - 1, -1, -1):
            vehicle = current["vehicles"][v]
            if end_candidate < vehicle["time_window"][1]:
                if end_candidate < vehicle["time_window"][0]:
                    # Discard vehicle since its time window is past
                    # end_candidate.
                    current["vehicles"].pop(v)
                else:
                    # Reduce time window for vehicle.
                    vehicle["time_window"][1] = end_candidate

        # Solve updated variant
        current_sol = solve(current, cl_args)

        if current_sol["summary"]["unassigned"] == 0:
            current_sol["origin"] = "dichotomy"
            solutions.append(current_sol)
            latest = end_candidate
        else:
            earliest = end_candidate

        end_candidate = int(round(float(earliest + latest) / 2))

    return solutions


def plot_pareto_front(indicators, pareto_plot_file, full_Y_scale=False):
    fig, ax1 = plt.subplots(1, 1)
    plt.xlabel("Completion time")
    plt.ylabel("Cost")

    options = {
        "dichotomy": {"marker": "^", "edgecolor": "red", "linewidth": 0.7},
        "backward_search": {"marker": "o", "edgecolor": "blue", "linewidth": 0.5},
    }

    ymax = indicators[0]["cost"]

    for origin in ["backward_search", "dichotomy"]:
        costs = [i["cost"] for i in indicators if i["origin"] == origin]
        if len(costs) == 0:
            continue
        completions = [i["completion"] for i in indicators if i["origin"] == origin]
        ymax = max(ymax, max(costs))

        ax1.scatter(
            completions,
            costs,
            facecolor="none",
            edgecolor=options[origin]["edgecolor"],
            marker=options[origin]["marker"],
            linewidth=options[origin]["linewidth"],
        )

    if full_Y_scale:
        ax1.set_ylim(0, ymax * 1.05)

    plt.savefig(pareto_plot_file, bbox_inches="tight")
    # plt.show()
    plt.close()


def backward_search(data, cl_args, first_solution):
    current = copy.deepcopy(data)
    current_sol = copy.deepcopy(first_solution)
    solutions = []

    end_dates = [r["steps"][-1]["arrival"] for r in first_solution["routes"]]
    latest = max(end_dates)

    for vehicle in current["vehicles"]:
        if "time_window" not in vehicle:
            vehicle["time_window"] = [0, latest]

    unassigned = first_solution["summary"]["unassigned"]

    while unassigned == 0:
        current_sol["origin"] = "backward_search"
        solutions.append(current_sol)

        # Reduce time window length for all vehicles.
        new_end = latest - 1
        for v in range(len(current["vehicles"]) - 1, -1, -1):
            vehicle = current["vehicles"][v]
            if new_end < vehicle["time_window"][1]:
                if new_end < vehicle["time_window"][0]:
                    # Discard vehicle since its time window is past
                    # new_end.
                    current["vehicles"].pop(v)
                else:
                    # Reduce time window for vehicle.
                    vehicle["time_window"][1] = new_end

        # Solve updated variant
        current_sol = solve(current, cl_args)

        unassigned = current_sol["summary"]["unassigned"]
        if len(current_sol["routes"]) > 0:
            latest = max([r["steps"][-1]["arrival"] for r in current_sol["routes"]])

    return solutions


def solve_asap(problem):
    init_solution = solve(problem["instance"], problem["cl_args"])

    if init_solution["code"] != 0:
        raise OSError(init_solution["code"], init_solution["error"])

    solutions = dichotomy(problem["instance"], problem["cl_args"], init_solution)

    if problem["pareto_front_more_solution"]:
        solutions.extend(
            backward_search(problem["instance"], problem["cl_args"], init_solution)
        )

    # Sort solutions by increasing completion time.
    solutions.sort(
        key=lambda sol: max([r["steps"][-1]["arrival"] for r in sol["routes"]])
    )
    filter_dominated(solutions)
    filter_unique(solutions)

    if len(problem["pareto_plot_file"]) > 0:
        indicators = [
            {
                "completion": max([r["steps"][-1]["arrival"] for r in sol["routes"]]),
                "cost": sol["summary"]["cost"],
                "origin": sol["origin"],
            }
            for sol in solutions
        ]

        plot_pareto_front(indicators, problem["pareto_plot_file"])

    if problem["return_pareto_front"]:
        for sol in solutions:
            sol.pop("origin", None)
        return solutions
    else:
        # Return solution with smallest completion time.
        solutions[0].pop("origin", None)
        solutions[0]["summary"].pop("computing_times", None)

        return solutions[0]
