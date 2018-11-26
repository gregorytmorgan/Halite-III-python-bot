# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

from hlt.positionals import Position

import numpy as np
import logging

class CellBlock:
    """
    Collection of cells
    """
    def __init__(self, game, position, width, height):
        self.game = game
        self.w = width
        self.h = height
        self.position = position
        self.positions = self.calc_positions(position, width, height)
        self.cell_values = np.array([width, height])

        cell_vals = [[0 for i in range(width)] for j in range(height)]

        for p in self.positions:
            cell = game.game_map[p]
            cell_vals[p.x - position.x][p.y - position.y] = cell.halite_amount

        self.cell_values = np.array(cell_vals)

    def get_cells(self):
        """
        Get an WxH array of MapCells
        """
        cells = []

        for p in self.positions:
            cells.append(self.game.game_map[p])

        return cells

    def get_values(self):
        """
		Returns a numpy array of cell values
        """
        return self.cell_values

    def get_sum(self):
        """
        Return the dum of all the halite in the block of cells
        """
        return self.cell_values.sum()

    def get_mean(self):
        """
        Return the mean amout of halite in the block of cells
        """
        return self.cell_values.mean()

    def get_max(self):
        """
        Return the max amount of halite in the block of cells
        """
        return self.cell_values.max()

    def get_positions(self):
        return self.positions

    @staticmethod
    def calc_positions(position, w, h):
        """
		Returns a list of cell positions
        """
        positions = []
        for y in range(position.y, position.y + h):
            for x in range(position.x, position.x + w):
                positions.append(Position(x, y))

        return positions

    @staticmethod
    def calc_offsets(w, h):
        """
		Returns a list of offets from the cell block position
        """
        offsets = []
        for y in range(0, h):
            for x in range(0, w):
                offsets.append((x, y))

        return offsets

    @staticmethod
    def get_corner_offset(direction, w, h):
        """
        Returns a tuple containing the offsets for the upper left corner of each direction
        """
        if type(direction) is tuple:
            direction = Direction.convert(direction)

        if direction == "n":
            return (-round((w - 1)/2), -h)
        elif direction == "s":
            return (-round((w - 1)/2), 1)
        elif direction == "e":
            return (1, -h)
        elif direction == "w":
            return (-w, -round((h - 1)/2))
        else:
            raise IndexError

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return "{}({}x{})@({}, {})".format(self.__class__.__name__,
                                   self.w,
                                   self.h,
                                   self.position.x,
                                   self.position.y)

