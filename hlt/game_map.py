import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
import logging

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

    def move_cost(self, a, b, move_cost = "turns"):
        # ignore 'a' since the cost is only a function of the current cell

        halite_amount = self[a].halite_amount

        if move_cost == "turns":
            return 1
        elif move_cost == "halite":
            return halite_amount * .1
        else:
            raise RuntimeError("Unknown nav move_cost: " + str(move_cost))

    def heuristic(self, start, end):
        dx = abs(start.x - end.x)
        dy = abs(start.y - end.y)

        #Use Chebyshev distance heuristic if we can move one square either adjacent or diagonal
        #D = 1
        #D2 = 1
        #Chebyshev = D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)

        # manhatten
        manhatten = dx + dy

        return manhatten

    #
    #
    # algorithm: 'astar', 'naive'
    #   'astar' takes args: 'move_cost': 'turns'|'halite'
    #   'naive' takes no args
    def navigate(self, ship, destination, algorithm="astar", args={}):
        if algorithm == "astar":
            move_cost = args["move_cost"] if "move_cost" in args else None
            path, cost = self.astar(ship, destination, move_cost)
        elif algorithm == "naive":
            path, cost = self.get_naive_path(ship, destination)
        else:
            logging.info("Error unknown navigate algorithm {}".format(algorithm))
            path, cost = None, None

        return path, cost

    #
    #
    #
    def get_naive_path(self, ship, destination):
        umoves = self.get_unsafe_moves(ship.position, destination)
        first_move = umoves[0]

        first_position =  Position(ship.position.x + first_move[0], ship.position.y + first_move[1])
        path = [first_position]

        step = 1 if destination.x > ship.position.x else -1
        x = ship.position.x
        if destination.x != ship.position.x:
            for x in range(first_position.x + step,  destination.x + step, step):
                path.append(Position(x, first_position.y))

        step = 1 if destination.y > ship.position.y else -1
        if destination.y != ship.position.y:
            for y in range(first_position.y + step,  destination.y + step, step):
                path.append(Position(x, y))

        path.reverse()

        return path, len(path)

    #
    # Get a path using a-star search, cost function can use 'halite' or 'turns'
    #
    def astar(self, ship, destination, move_cost="turns"):

        # return None if no soln, returns empty list with zero cost if start == end,
        # otherwise returns a path list and a cumlative cost

        G = {} #Actual movement cost to each position from the start position
        F = {} #Estimated movement cost of start to end going via this position

        start = self.normalize(ship.position)
        end = self.normalize(destination)

        if start == end:
            return [], 0 #Done!

        if self.DEBUG: logging.info("{} -> {}".format(start, end)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

        #Initialize starting values
        G[start] = 0
        F[start] = self.heuristic(start, end)

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
                    if self.DEBUG: logging.info("updating current score to: {}".format(F[pos])) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
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

                #path.reverse()
                path.pop() # remove the start point
                return path, F[end] # Done!

            #Mark the current vertex as closed

            if self.DEBUG: logging.info("removing {} from openVertices".format(current)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

            openVertices.remove(current)

            if self.DEBUG: logging.info("adding {} to closedVertices".format(current)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

            closedVertices.add(current)

            #Update scores for vertices near the current position
            #for neighbour in graph.get_vertex_neighbours(current):

            #neighbours = self.get_vertex_neighbours(current)

            neighbours = []
            for n in current.get_surrounding_cardinals():
                neighbours.append(n)

            if self.DEBUG: logging.info("neighbours for {}: {}".format(current, neighbours))

            for neighbour in neighbours:

                if self.DEBUG: logging.info("neighbour: {}".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG

                if neighbour in closedVertices:
                    if self.DEBUG: logging.info("skipping neighbour {}, already checked".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    continue #We have already processed this node exhaustively

                cost = self.move_cost(current, neighbour, move_cost)

                candidateG = G[current] + cost

                if neighbour not in openVertices:
                    if self.DEBUG: logging.info("Discovered a new cell {}, adding to  openVertices".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    openVertices.add(neighbour) #Discovered a new vertex
                elif candidateG >= G[neighbour]:
                    if self.DEBUG: logging.info("Ignoring cell {}, cost is too high".format(neighbour)) # DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG
                    continue #This G score is worse than previously found

                #Adopt this G score
                cameFrom[neighbour] = current
                G[neighbour] = candidateG
                H = self.heuristic(neighbour, end)
                F[neighbour] = G[neighbour] + H

        #raise RuntimeError("A* failed to find a solution")
        return None, None

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