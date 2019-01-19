import logging

from hlt.entity import Ship

from myutils.constants import DEBUG, DEBUG_GAME

class Task():
    """
    Ship task
    """
    id = 0

    def __init__(self, task_name, turn_action = lambda game, ship: True, on_complete = lambda game, ship, retval: False):

        self.task_name = task_name
        self.priority = 5
        self.on_complete = on_complete
        self.turn_action = turn_action
        self.ships = []
        self.active = True
        self.ships_required = 1
        #self.game = game ???

        self.id = Task.id + 1

        Task.id += 1

    def turn(self, game, ship):
        retval = self.turn_action(game, ship)

        if retval is False:
            return False
        else:
            return self.on_complete(game, ship, retval)

    def abort(self):
        pass

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash("{}.{}".format(self.__class__.__name__, self.id, self.task_name))

    def __repr__(self):
        return "id:{}, ships:{}, ships_required:{}, active:{}".format(self.id, self.ships, self.ships_required, self.active)


#
# Task manager is work in progress/not tested
#
# For now simply add task manually to a ships tasks list.
#
class Task_Manager():

    def __init__(self, game):
        self.game = game
        self.tasks = []

    def task_get(self, target = None):
        """
        Get the task list
        """
        retval = []

        if isinstance(target, Ship):
            retval = []
            for t in self.tasks.values():
                if target.id in t.ships:
                    retval.append(t)
        elif isinstance(target, int):
            if target in self.tasks:
                retval.append(self.tasks[target])
        elif target is None:
            retval = self.tasks
        else:
            raise RuntimeError("Invalid target: ".format(target))

        return retval


    def task_assign(self, task, target_ship):
        """
        Assign a task
        """

        me = self.game.me

        if isinstance(target_ship, int):
            if me.has_ship(target_ship):
                ship = me.get_ship(target_ship)
        elif isinstance(target_ship, Ship):
            ship = target_ship
        else:
            raise RuntimeError("Invalid target_ship: ".format(target_ship))

        if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is tasked with '{}'".format(ship.id, task.task_name))

        #ship_states[ship.id]["status"] = "tasked"
        ship.status = "tasked"
        task.ships.append(ship.id)
        ship.tasks.append(task.id)


    def task_abort(self, ship_id = None, task_id = None):
        """
        Abort a task
        """

        logging.debug("args ship: {} task: {}".format(ship_id, task_id))

        if not (ship_id is None) and not (task_id is None):
            logging.debug("aborting by ship and task")
            return self.task_abort_by_task(task_id, ship_id) # use abort_by_task ... logging is better
        elif not (ship_id is None):
            logging.debug("aborting by ship {}".format(ship_id))
            return self.task_abort_by_ship(ship_id)
        elif not (task_id is None):
            logging.debug("aborting by task {}".format(task_id))
            return self.task_abort_by_task(task_id)
        else:
            raise RuntimeError("Task id or ship id required")


    def task_abort_by_ship(self, ship_id, task_id = None):
        """
        Abort a task
        """

        me = self.game.me

        logging.debug("aborting by ship: {} and task: {}".format(ship_id, task_id))

        if not me.has_ship(ship_id):
            logging.warning("Ship {} does not exist. Abort failed.".format(ship))
            return False

        ship = me.get_ship(ship_id)

        if task_id is None:
            if task_id in self.tasks and ship_id in t.ships:
                Tasks[task_id].ships.remove(ship_id)
            ship.tasks.clear()
            ship.status = "exploring" # default status = exploring
        else:
            if task_id in ship.tasks:
                ship.tasks.remove(task_id)
                if not ship.tasks:
                    ship.status = "exploring" # default status = exploring
            if ship.id in self.tasks:
                self.tasks.remove(task_id)

        if DEBUG & (DEBUG_GAME): logging.info("GAME - Task {} aborted".format(ship.id))

        return True


    def task_abort_by_task(self, task_id, ship_id = None):
        """
        Abort a task
        """
        me = self.game.me

        if not (task_id in self.tasks):
            logging.warning("Task {} does not exist. Abort failed.".format(task))
            return False

        task = self.tasks[task_id]

        if ship_id is None:
            for sid in task.ships:
                if me.has_ship(sid):
                    ship = me.get_ship(sid)
                    task.ships.remove(sid)
                    if task.id in ship.tasks:
                        ship.tasks.remove(task.id)
                        if not ship.tasks:
                            ship.status = "exploring" # default status = exploring
                        if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} aborted task '{}'".format(ship.id, task.task_name))
                    else:
                        logging.warning("Ship {} is missing task {} from its task list.".format(ship.id, task.id))
                else:
                    logging.warning("Ship {} is missing, can not abort.".format(sid))
        else:
            if ship_id in task.ships:
                task.ships.remove(ship_id)

            if me.has_ship(ship_id):
                ship = me.get_ship(ship_id)
                if task.id in ship.tasks:
                    ship.tasks.remove(task.id)
                    if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} aborted task '{}'".format(ship.id, task.task_name))
                    if not ship.tasks:
                        ship.status = "exploring"
                else:
                    logging.warning("Ship {} is missing task {} from its task list.".format(ship.id, task.id))
            else:
                logging.warning("Ship {} does not exist. Abort failed.".format(ship_id))

        return True