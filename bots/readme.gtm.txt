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



