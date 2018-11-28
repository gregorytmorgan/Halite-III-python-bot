import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
import logging
import time
import numpy as np
import copy

from myutils.constants import DEBUG, DEBUG_NAV

class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.position = position
        self.halite_amount = halite_amount
        self.ship = None
        self.structure = None

    @property
    def is_empty(self):
        """
        :return: Whether this cell has no ships or structures
        """
        return self.ship is None and self.structure is None

    @property
    def is_occupied(self):
        """
        :return: Whether this cell has any ships
        """
        return self.ship is not None

    @property
    def has_structure(self):
        """
        :return: Whether this cell has any structures
        """
        return self.structure is not None

    @property
    def structure_type(self):
        """
        :return: What is the structure type in this cell
        """
        return None if not self.structure else type(self.structure)

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def mark_safe(self):
        """
        Mark this cell as safe (unoccupied) for navigation.

        """
        self.ship = None

    def __eq__(self, other):
        return self.position == other.position

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'MapCell({}, halite={})'.format(self.position, self.halite_amount)


class GameMap:
    """
    The game map.

    Can be indexed by a position, or by a contained entity.
    Coordinates start at 0. Coordinates are normalized for you
    """

    DEBUG = False

    def __init__(self, cells, width, height):
        self.width = width
        self.height = height
        self._cells = cells

        # init the coord map
        self._coord_map = np.empty((self.width, self.height), dtype=object)

        for y in np.arange(self.height):
            for x in np.arange(self.width):
                self._coord_map[x][y] = Position(y, x)

        # init the halite map
        self._halite_map = np.empty((self.width, self.height), dtype="float32")

        for y in range(self.height):
            for x in range(self.width):
                self._halite_map[y][x] = self._cells[y][x].halite_amount

    def __getitem__(self, location):
        """
        Getter for position object or entity objects within the game map
        :param location: the position or entity to access in this map
        :return: the contents housing that cell or entity
        """
        if isinstance(location, Position):
            location = self.normalize(location)
            return self._cells[location.y][location.x]
        elif isinstance(location, Entity):
            return self._cells[location.position.y][location.position.x]
        return None

    def calculate_distance(self, source, target):
        """
        Compute the Manhattan distance between two locations.
        Accounts for wrap-around.
        :param source: The source from where to calculate
        :param target: The target to where calculate
        :return: The distance between these items
        """
        source = self.normalize(source)
        target = self.normalize(target)
        resulting_position = abs(source - target)
        return min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)

    def normalize(self, position):
        """
        Normalized the position within the bounds of the toroidal map.
        i.e.: Takes a point which may or may not be within width and
        height bounds, and places it within those bounds considering
        wraparound.
        :param position: A position object.
        :return: A normalized position object fitting within the bounds of the map
        """
        return Position(position.x % self.width, position.y % self.height)

    @staticmethod
    def _get_target_direction(source, target):
        """
        Returns where in the cardinality spectrum the target is from source. e.g.: North, East; South, West; etc.
        NOTE: Ignores toroid
        :param source: The source position
        :param target: The target position
        :return: A tuple containing the target Direction. A tuple item (or both) could be None if within same coords
        """
        return (Direction.South if target.y > source.y else Direction.North if target.y < source.y else None,
                Direction.East if target.x > source.x else Direction.West if target.x < source.x else None)

    def get_unsafe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move mechanic does not account for collisions. The multiple directions are if both directional movements
        are viable.
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        source = self.normalize(source)
        destination = self.normalize(destination)
        possible_moves = []
        distance = abs(destination - source)
        y_cardinality, x_cardinality = self._get_target_direction(source, destination)

        if distance.x != 0:
            possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                  else Direction.invert(x_cardinality))
        if distance.y != 0:
            possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                  else Direction.invert(y_cardinality))
        return possible_moves

    def naive_navigate(self, ship, destination):
        """
        Returns a singular safe move towards the destination.

        :param ship: The ship to move.
        :param destination: Ending position
        :return: A direction.
        """
        # No need to normalize destination, since get_unsafe_moves does that
        for direction in self.get_unsafe_moves(ship.position, destination):
            target_pos = ship.position.directional_offset(direction)
            if not self[target_pos].is_occupied:
                self[target_pos].mark_unsafe(ship)
                return direction

        return Direction.Still

    def move_cost(self, a, b, move_cost_type = "turns"):
        # ignore 'a' since the cost is only a function of the current cell

        if move_cost_type == "turns":
            return 1
        elif move_cost_type == "halite":
            return self[a].halite_amount * .1
        else:
            raise RuntimeError("Unknown nav move_cost_type: " + str(move_cost_type))

    def heuristic(self, start, current, goal, move_cost_type = "turns"):
        manhatten = self.calculate_distance(current, goal)

        if move_cost_type == "turns":
            dx1 = current.x - goal.x
            dy1 = current.y - goal.y
            dx2 = start.x - goal.x
            dy2 = start.y - goal.y
            cross = abs(dx1 * dy2 - dx2 * dy1)
            retval = manhatten + cross * 0.001
        elif move_cost_type == "halite":
            retval = manhatten * constants.MAX_HALITE

        return retval

    def navigate(self, start, destination, algorithm="astar", args={}):
        """
        algorithm: 'astar', 'naive'
          'astar' - takes args: 'move_cost': 'turns'|'halite'
          'naive' - takes no args
          'dock' - takes no args
        """
        if algorithm == "astar":
            move_cost = args["move_cost"] if "move_cost" in args else None
            path, cost = self.astar(start, destination, move_cost)
        elif algorithm == "naive":
            path, cost = self.get_naive_path(start, destination)
        elif algorithm == "dock":
            path, cost = self.get_docking_path(start, destination)
        else:
            logging.info("Error - Unknown navigate algorithm {}".format(algorithm))
            path, cost = None, None

        return path, cost

    #
    # return None if no soln, returns empty list with zero cost if start == end,
    # otherwise returns a path list and a cumlative cost
    #
    def get_naive_path(self, start, destination):

        if start == destination:
            return [], 0

        distance = abs(destination - start)
        y_cardinality, x_cardinality = self._get_target_direction(start, destination)

        x_direction = x_cardinality if distance.x < (self.width / 2) else Direction.invert(x_cardinality)
        y_direction = y_cardinality if distance.y < (self.height / 2) else Direction.invert(y_cardinality)

        logging.debug("x_direction:{}, y_direction:{}".format(x_direction, y_direction))

        umoves = self.get_unsafe_moves(start, destination)
        first_move = umoves[0]

        first_position =  Position(start.x + first_move[0], start.y + first_move[1])
        path = [first_position]

        step = x_direction[0]
        x = first_position.x
        for i in range(first_position.x + step,  destination.x + step, step):
            x = i
            path.append(Position(x, first_position.y))

        step = x_direction[1]
        if destination.y != start.y:
            for y in range(first_position.y,  destination.y + step, step):
                path.append(Position(x, y))

        path.reverse()

        return path, len(path)

    def get_docking_path(self, start, dropoff):
        """
        dock paths are north and south

        """
        if start.y == dropoff.y:
            path = [dropoff, Position(dropoff.x, dropoff.y - 1), Position(start.x, start.y - 1) ] # dock to the North
            cost = 2
        else:
            path, cost = self.get_naive_path(start, Position(dropoff.x, start.y))
            path.insert(0, dropoff)
        return path, cost

    #
    # Get a path using a-star search, cost function can use 'halite' or 'turns'
    #
    # return None if no soln, returns empty list with zero cost if start == end,
    # otherwise returns a path list and a cumlative cost
    #
    def astar(self, start, destination, move_cost_type="turns"):
        astar_start_time = time.time()

        G = {} #Actual movement cost to each position from the start position
        F = {} #Estimated movement cost of start to end going via this position

        start = self.normalize(start)
        end = self.normalize(destination)

        if start == end:
            return [], 0 #Done!

        if self.DEBUG: logging.info("{} -> {}".format(start, end)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

        #Initialize starting values
        G[start] = 0
        F[start] = self.heuristic(start, start, end, move_cost_type)

        closedVertices = set()
        openVertices = set([start])

        if self.DEBUG: logging.info("start: adding {} to openVertices".format(start)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

        cameFrom = {}

        while len(openVertices) > 0:
            #Get the vertex in the open list with the lowest F score
            current = None
            currentFscore = None

            for pos in openVertices:
                if current is None or F[pos] < currentFscore:
                    if self.DEBUG: logging.info("updating current score with F score ({}) from {}".format(F[pos], pos)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    currentFscore = F[pos]
                    current = pos

            #Check if we have reached the goal
            if current == end:
                if self.DEBUG: logging.info("reached goal: {}".format(end)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

                #Retrace our route backward
                path = [current]
                while current in cameFrom:
                    current = cameFrom[current]
                    path.append(current)

                path.pop() # remove the start point

                if DEBUG & (DEBUG_NAV): logging.info("Nav - Total A* elapsed time {}".format(round(time.time() - astar_start_time, 4))) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

                return path, F[end] # Done!

            #Mark the current vertex as closed
            openVertices.remove(current)
            if self.DEBUG: logging.info("removing {} from openVertices".format(current)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

            closedVertices.add(current)
            if self.DEBUG: logging.info("adding {} to closedVertices".format(current)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

            #Update scores for vertices near the current position
            #for neighbour in graph.get_vertex_neighbours(current):
            for neighbour in current.get_surrounding_cardinals():
                neighbour = self.normalize(neighbour)
                if self.DEBUG: logging.info("neighbour: {}".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

                if neighbour in closedVertices:
                    if self.DEBUG: logging.info("skipping neighbour {}, already checked".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    continue #We have already processed this node exhaustively

                candidateG = G[current] + self.move_cost(current, neighbour, move_cost_type)

                if neighbour not in openVertices:
                    if self.DEBUG: logging.info("Discovered a new cell {}, adding to  openVertices.".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    openVertices.add(neighbour) #Discovered a new vertex
                elif candidateG >= G[neighbour]:
                    if self.DEBUG: logging.info("Ignoring candiate cell {}, cost is too high at {}".format(neighbour, round(candidateG, 4))) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    continue #This G score is worse than previously found

                #Adopt this G score
                cameFrom[neighbour] = current
                G[neighbour] = candidateG
                H = self.heuristic(start, neighbour, end, move_cost_type)
                F[neighbour] = G[neighbour] + H
                if self.DEBUG: logging.info("Neighbour elapsed time {}".format(round(time.time() - astar_start_time, 4)))

        return None, None

    def get_dense_areas():
        """
            NOT IMPLEMENTED - BROKEN
        """

        threshold = self.get_cell_value_map().max() * .8
        hottest_areas = np.ma.MaskedArray(cell_value_map, mask= [cell_value_map < threshold], fill_value = 0)

        #logging.debug("\n{}".format(hottest_areas.filled())) # std display with masked vals set to 0

        row, col = hottest_areas.nonzero()

        hotspots = []
        for y, x in zip(row, col):
            hotspots.append((x, y))
            #logging.debug("Position({},{}) = {}".format(x, y, hottest_areas[y][x]))

        peaks = []

        closed_points = set()

        for high_points in hotspots:
            peak = []
            open_points = set()
            open_points.add(high_points)
            current_val = None

            for pt in open_points:
                val = cell_value_map[pt[0]][pt[1]]

                logging.debug("val: {}".format(val))

                if current_val is None or (val <= current_val or val > .8 * current_val):
                    peak.append(pt)
#                    for n in get_adjacent(pt):
#                        open_points.add(n)

#                open_points.remove(pt)
#                closed_points.add(pt)

            peaks.append(peak)

        return []

    @staticmethod
    def _generate():
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, read_input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = read_input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height)

    def _update(self):
        """
        Updates this map object from the input given by the game engine
        :return: nothing
        """
        # Mark cells as safe for navigation (will re-mark unsafe cells
        # later)
        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].ship = None

        for _ in range(int(read_input())):
            cell_x, cell_y, cell_energy = map(int, read_input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy

    def get_halite_map(self):
        """
        Return the 2d map of halite amounts
        """
        return self._halite_map

    def get_coord_map(self):
        """
        Return the 2d map of positions - used by other calcs
        """
        return self._coord_map

    def get_distance_map(self, p):
        """
        Return the 2d map of distance beteen p and all map positions
        """
        v_calc_distance = np.vectorize(self.calculate_distance)

        return v_calc_distance(p, self._coord_map)

    def get_cell_value(self, p1, p2):
        """
        Get the value of a cell p2 given is halite amount and distance from p1
        """

        if (p2.y - p1.y) > 0:
            row_start = p1.y
            row_end = p2.y + 1
        else:
            row_start = p2.y
            row_end = p1.y + 1

        if (p2.x - p1.x) > 0:
            col_start = p1.x
            col_end = p2.x + 1
        else:
            col_start = p2.x
            col_end = p1.x + 1

        # use pre-computed values if shipyard or dropoff?
        distance = self.calculate_distance(p1, p2)
        halite = self[p2].halite_amount
        halite_map = self.get_halite_map() # used to get slice for avg cost. Not worth the cost?

        # need to copy since we're going to modify the slice with NaN. How expensive?
        avg_halite_map = copy.deepcopy(halite_map[row_start:row_end, col_start:col_end])

        #ignore start/end cells
        avg_halite_map[0][0] = np.nan
        avg_halite_map[-1][-1] = np.nan

        avg_halite_map = halite_map[row_start:row_end, col_start:col_end]

        if avg_halite_map.size == 0 : logging.error("Error - point {} has a avg halite map size of 0".format(p2))

        avg_halite = np.nanmean(avg_halite_map)

        fuel_cost = 0 if np.isnan(avg_halite) else round(distance * avg_halite * .1)

        # debug
        if False and (p2.y == 12 and p2.x == 4):
            logging.debug("Avg slice {}:".format(p2))
            logging.debug("\n{}".format(avg_halite_map))
            logging.debug("{} v:{} = h:{} - (d:{} * ah:{} * .1) [{}:{},{}:{}] {}".format(p2, round(halite - fuel_cost), halite, distance, round(avg_halite), row_start, row_end, col_start, col_end, avg_halite_map.shape))

        return halite - fuel_cost

    def get_cell_value_map(self, p):
        """
        Return the 2d map the value of a cell p and all other cells given it's halite amount and distance from p
        """
        value_map = np.empty((self.width, self.height), dtype=object)
        v_cell_value_map = np.vectorize(self.get_cell_value)

        return v_cell_value_map(p, self._coord_map)

    def __repr__(self):
        map = ""
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                cell = self[Position(x, y)]

                if cell.is_empty:
                    s = "{:<6d}".format(cell.halite_amount)
                elif cell.has_structure:
                    if cell.is_occupied:
                        s = "{:<6s}".format("[<" + str(cell.ship.id) + ">]")
                    else:
                        s = "{:<6s}".format("[ X ]")
                else:
                    s = "{:<6s}".format("<" + str(cell.ship.id) + ">")

                if row == "":
                    row = row + "{:<3d}{}".format(y, s)
                else:
                    row = row + "{}".format(s)

            map = map + row

        return map
