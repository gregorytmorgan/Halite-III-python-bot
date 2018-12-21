v6		Add simple collision detection/avoidance.

v7		Same as v6 but has a max of 6 bots vs 8 in v6.

v8		Change max ships 8 -> 6

v9		Update the backoff distance from a hard coded 8, now based on the number of ships

v10		Move toward dense cells.

v11		Increase cargo return threshold to max (1000).

v12		Fix loiter radius issues.

V13		Added A* nav

v14		Update get_density_move() to look at 3x3 block of cells instead of only one in each direction.

v15		Add traffic managment: lanes for shipyard entry/exit + departure points

v16		Add better collision handling.  Prevent enemy from blocking shipyard, on
		blocked entry wait vs random, on blocked exit try laterals moves. Plus when
		an exploring ship randomly enters the shipyard re-loiter it.

v17		Add hotspot bot assignment, fix a fair number of nav bugs, esp around entry/exit lanes.

v18		Add collision resolution

v19		Fix bug in get best block search/get_cell_blocks()

v20		Fix bug that caused prevented the cell_value_map from updating, Couple minor changes to help
		with collisions/congestion around the shipyard. Update the cell_value func to skip cells that
		have a value lower than the mining threshold + return 0 for negative values (Update: in
		hindsight this was bad!). Make target threshold dynamic based on mining rate to ensure we
		generate enought targets.

v21		Fix corner offset bug that caused problems in the best block search. Only add a plus_one move
		if the best cell is different than the next cell. Add simple logic to skip fueling when returning.

v22		Rework base blocking protection from v21. Implement anti-blocking scheme for base adjacent cells.
		Fix logic bug in calculating value of moving vs mining. (Update: this version resulted in a lose of rank)

v23		Fix base blocking bugs. Don't discard cells with halite < the default mining threshold + don't
		clamp cell values to 0+, these two items will cause a shortage of targets. Chk loiter assignment
		halite is larger than mining threshold, If best block search fails, research with lower threshold.

