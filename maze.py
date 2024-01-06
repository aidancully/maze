import numpy as np
import random
import itertools


# A representation of a maze.
#
# I use a Numpy ndarray, where each bit represents whether or not there
# is a wall on that axis at the opening edge of the cell. This
# representation easily allows for more than 2 dimensions, though only
# 2D mazes are used for the game.
class Maze:
    class Constant:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return self.name

    FORWARD = Constant("forward")
    BACKWARD = Constant("backward")
    WALL = Constant("wall")
    NOWALL = Constant("nowall")

    # After the maze is created, the interior consists of every wall
    # being filled in.
    def __init__(self, *sizes):
        assert all(isinstance(x, int) and x > 0 for x in sizes)
        assert len(sizes) <= 7
        self.shape = sizes
        all_walls = (2 ** len(sizes)) - 1
        # x + 1, because we have to store the terminating wall.
        walldims = [x + 1 for x in sizes]
        self.walls = np.full(walldims, all_walls, dtype=np.int8)
        # outermost edges only contain a wall pointing inwards
        indexer = [slice(x + 1) for x in sizes]
        for dim in range(len(sizes)):
            indexer[dim] = -1
            self.walls[tuple(indexer)] &= 2**dim
            indexer[dim] = slice(sizes[dim] + 1)

    def _normalize_walkidx(self, pos):
        assert len(pos) == 3
        start = pos[0]
        dim = pos[1]
        dir = pos[2]

        assert len(start) == len(self.walls.shape)
        assert isinstance(dim, int)
        assert dim <= len(self.walls.shape)

        if dir is self.__class__.FORWARD:
            start = list(start)
            start[dim] += 1
        else:
            assert dir is self.__class__.BACKWARD

        assert all(
            [
                isinstance(start[dimidx], int)
                and start[dimidx] >= 0
                and start[dimidx] < self.walls.shape[dimidx]
                for dimidx in range(len(start))
            ]
        )
        return tuple(start), dim

    def __setitem__(self, pos, value):
        start, dim = self._normalize_walkidx(pos)
        if value is self.__class__.WALL:
            self.walls[start] |= 2**dim
        else:
            assert value is self.__class__.NOWALL
            self.walls[start] &= ~(2**dim)

    def __getitem__(self, pos):
        start, dim = self._normalize_walkidx(pos)
        if bool(self.walls[start] & (2**dim)):
            return self.__class__.WALL
        else:
            return self.__class__.NOWALL

    def walk(self, start, dim, dir):
        if self[(start, dim, dir)] is self.__class__.WALL:
            raise Exception("walk through walls")
        add = 1
        if dir is self.BACKWARD:
            add = -1
        ret = list(start)
        ret[dim] += add
        return tuple(ret)


def cartesian_generator(shape):
    return itertools.product(*(range(x) for x in shape))


# Use Wilson's Algorithm (https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm)
# to generate a maze. Use an iterator interface, where each iteration
# value is a path that the player will be allowed to walk. (It's up to
# the caller remove those walls from the generated maze. Maybe that
# isn't ideal?) Using an iterator lets us draw a graphic while we're
# initializing the maze.
class MazeGenerator:
    def __init__(self, empty_maze):
        self.maze = empty_maze
        self.in_maze = np.zeros(tuple(empty_maze.shape), dtype=np.bool_)
        self.first = tuple([random.randint(0, x - 1) for x in empty_maze.shape])
        self.in_maze[self.first] = True
        self.maze_iterator = cartesian_generator(self.in_maze.shape)

    def start_path(self):
        for pos in self.maze_iterator:
            if not self.in_maze[pos]:
                return pos
        return None

    def __iter__(self):
        return self

    def __next__(self):
        pos = self.start_path()
        if pos is None:
            raise StopIteration()
        maybepath = [pos]
        axes = []
        directions = []
        while not self.in_maze[pos]:
            next_axis = random.randint(0, self.in_maze.ndim - 1)
            next_dir = [Maze.FORWARD, Maze.BACKWARD][random.randint(0, 1)]
            attempt = list(pos)
            if next_dir is Maze.FORWARD:
                attempt[next_axis] += 1
                if attempt[next_axis] >= self.in_maze.shape[next_axis]:
                    attempt = None
            else:
                attempt[next_axis] -= 1
                if attempt[next_axis] < 0:
                    attempt = None
            if not attempt:
                continue
            attempt = tuple(attempt)

            try:
                idx = maybepath.index(attempt)
                del maybepath[(idx + 1) :]
                del axes[idx:]
                del directions[idx:]
                pos = attempt
                attempt = None
            except ValueError:
                pos = attempt
                maybepath.append(attempt)
                axes.append(next_axis)
                directions.append(next_dir)
        for el in maybepath:
            self.in_maze[el] = True
        return zip(maybepath[:-1], axes, directions)
