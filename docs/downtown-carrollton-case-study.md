# Case Study: Full-Network Schedule Simulation & Passenger Trade-off Analysis

## Executive Summary
Transit networks are highly coupled systems. Optimizing a schedule to fix a transfer bottleneck at one station frequently causes unintended cascading failures at downstream stations. 

The DART Transit Optimizer was built to replace single-hub guesswork with a full-network simulation engine. By running exhaustive GTFS schedule shifts through a rules-based matcher, this tool quantifies the exact trade-offs of proposed schedule changes, measuring both operational vehicle feasibility and net passenger wait-time impacts across the entire system.

## The Simulation Scenario
To demonstrate the engine's capabilities, we simulated a schedule adjustment to the **GREEN Line (Direction 0)**, advancing its departure times by **3 minutes (-180 seconds)** across the network. 

The objective was to evaluate whether a localized improvement at a major hub justifies the resulting network-wide ripple effects.

### 1. Operational Feasibility (Vehicle Blocks & Layovers)
Before evaluating passenger impacts, any schedule change must be physically possible for the fleet. Standard GTFS routing tools often assume infinite flexibility, ignoring that buses and trains belong to physical blocks with mandated driver recovery times.

**Simulation Result: FEASIBLE**
* The simulation engine grouped all active GREEN Line trips by their operational `block_id`.
* Every shifted trip was exhaustively evaluated against its incoming and outgoing scheduled layover buffers.
* The -3 minute shift maintained a minimum remaining layover of **120.0 seconds** across all evaluated vehicle blocks, resulting in **0 violating trips**. The shift is operationally viable.

### 2. Localized Success: The Target Hub (`cluster_14`)
The primary benefit of this shift was observed at `cluster_14`, where passengers transferring from local buses to the GREEN line frequently experience near-miss connections. 

By advancing the GREEN line schedule by 3 minutes, the engine recorded a massive localized improvement for passengers transferring from **Route 018**:
* **Rescued Near-Misses:** 178 connections
* **Passenger Wait-Minutes Saved:** 2,757.5 minutes

However, even at the exact same hub, this change was not universally positive. The advanced train departure broke existing tight connections for passengers arriving on **Route 023**:
* **Newly Created Misses:** 91 connections
* **Passenger Wait-Minutes Added:** 337.5 minutes

### 3. The Ripple Effect: Downstream Impacts (`cluster_107`)
The true value of the simulator is revealing downstream damage. At `cluster_107`, the 3-minute GREEN line shift created a near-even trade-off for local bus transfers, but severely damaged rail-to-rail transfers.

**Local Bus Transfer Impacts at `cluster_107`:**
* **Route 207 to GREEN:** Rescued 35 misses (Saved 291.0 wait-minutes).
* **Route 213 to GREEN:** Created 36 new misses (Added 308.0 wait-minutes).
* *Net Impact:* A zero-sum trade-off for bus passengers.

**Rail-to-Rail Transfer Impacts at `cluster_107`:**
* **ORANGE Line to GREEN Line:** Created **53 new misses**, adding a staggering **758.0 wait-minutes** for rail passengers.

## Conclusion & Business Value
This simulation output provides transit planners with a mathematically sound trade-off ledger. While the -3 minute shift on the GREEN Line successfully rescues 178 critical connections and saves nearly 2,800 passenger wait-minutes at `cluster_14`, the planner must now weigh that localized victory against the 758 minutes of delay introduced to ORANGE Line passengers downstream.

By surfacing these hidden network costs and verifying block feasibility computationally, the DART Transit Optimizer transforms schedule adjustments from a guessing game into a data-driven engineering decision.