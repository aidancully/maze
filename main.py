#!/usr/bin/env python

import sys
import pygame
import pygame.joystick
import math
import maze

DIFFICULTY = 10


def maybe_incr(col):
    if col == 0:
        return col
    return col + 1


class Player:
    # The kids wanted a character with a straw hat, for some reason.
    CHARACTER = [
        [0, 0, 0, 0, 0, 1, 1, 1, 1],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
        [0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1],
        [0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1],
        [0, 0, 0, 1, 0, 0, 1, 0, 0, 1],
        [0, 0, 0, 0, 1, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1, 1, 1],
    ]
    # When you reach the goal, the character changes color.
    WIN_CHARACTER = [[maybe_incr(col) for col in row] for row in CHARACTER]
    PALETTE = [
        (0, 0, 0, 0),
        (255, 128, 128, 0),
        (255, 0, 0, 0),
    ]

    def _init_picture(self, character):
        dim_x = max([len(x) for x in character]) + 2
        dim_y = len(character) + 2
        picture = pygame.Surface((dim_x, dim_y))
        for y in range(dim_y):
            for x in range(dim_x):
                color = self.__class__.PALETTE[0]
                try:
                    if x > 0 and y > 0:
                        color = self.__class__.PALETTE[character[y - 1][x - 1]]
                except Exception:
                    pass
                picture.set_at((x, y), color)
        return picture

    def __init__(self):
        self.picture = self._init_picture(self.__class__.CHARACTER)
        self.win_picture = self._init_picture(self.__class__.WIN_CHARACTER)


# This is a simple class that will help us print to the screen. Not
# currently used.
class TextPrint(object):
    def __init__(self):
        self.reset()
        self.font = pygame.font.Font(None, 20)

    def tprint(self, screen, textString):
        textBitmap = self.font.render(textString, True, (255, 255, 255))
        screen.blit(textBitmap, (self.x, self.y))

    def reset(self):
        self.x = 10
        self.y = 10
        self.line_height = 15

    def indent(self):
        self.x += 10

    def unindent(self):
        self.x -= 10


# The controller attached to my RPi uses this for the button labeled
# START.
BUTTON_START = 9

# Arrow keys, for keyboard control.
KEYDOWN = 81
KEYUP = 82
KEYLEFT = 80
KEYRIGHT = 79


class DrawMaze:
    def __init__(self, game, mase):
        self.game = game
        self.view = self.game.view
        self.maze = mase
        self.view.erase()
        self.indices = maze.cartesian_generator(self.maze.walls.shape)

    def __iter__(self):
        return self

    def __next__(self):
        coord = next(self.indices)
        wall = self.maze.walls[tuple(coord)]
        blitrects = []
        if coord[0] == self.maze.shape[0] - 1 and coord[1] == self.maze.shape[1] - 1:
            rect = pygame.Rect(
                coord[0] * self.view.block_size + self.view.wall_size,
                coord[1] * self.view.block_size + self.view.wall_size,
                self.view.block_size - self.view.wall_size,
                self.view.block_size - self.view.wall_size,
            )
            pygame.draw.rect(self.view.maze_surface, (255, 0, 0), rect)
            blitrects.append(rect)
        if (wall & 2) != 0:
            # draw wall on top
            rect = pygame.Rect(
                coord[0] * self.view.block_size,
                coord[1] * self.view.block_size,
                self.view.block_size + self.view.wall_size,
                self.view.wall_size,
            )
            pygame.draw.rect(self.view.maze_surface, (255, 255, 255), rect)
            blitrects.append(rect)
        if (wall & 1) != 0:
            # draw wall on top
            rect = pygame.Rect(
                coord[0] * self.view.block_size,
                coord[1] * self.view.block_size,
                self.view.wall_size,
                self.view.block_size + self.view.wall_size,
            )
            pygame.draw.rect(self.view.maze_surface, (255, 255, 255), rect)
            blitrects.append(rect)
        if len(blitrects) > 0:
            blitrect = blitrects[0]
            for rect in blitrects[1:]:
                blitrect.union_ip(rect)
            self.view.update_maze_surface(blitrect)
        return None

    def next_phase(self):
        self.game.set_maze(self.maze)
        return None


class DrawMazeGeneration:
    def __init__(self, game):
        self.game = game
        self.view = self.game.view
        self.maze = maze.Maze(self.view.block_count, self.view.block_count)
        self.generator = maze.MazeGenerator(self.maze)
        self.path = None

    def __iter__(self):
        return self

    def __next__(self):
        start, axis, direction = None, None, None
        while start is None:
            if self.path is None:
                self.path = next(self.generator)
            start, axis, direction = next(self.path, (None, None, None))
            if start is None:
                self.path = None

        self.maze[start, axis, direction] = maze.Maze.NOWALL
        drawrect = pygame.Rect(
            start[0] * self.view.block_size,
            start[1] * self.view.block_size,
            self.view.block_size,
            self.view.block_size,
        )
        pygame.draw.rect(self.view.maze_surface, (255, 255, 255), drawrect)
        self.view.update_maze_surface(drawrect)
        return None

    def next_phase(self):
        return DrawMaze(self.game, self.maze)


class View:
    def __init__(self, screen, block_count):
        self.screen = screen
        sq_size = min(screen.get_width(), screen.get_height())
        self.block_count = block_count
        self.wall_size = sq_size // (block_count * 5 + 1)
        self.block_size = self.wall_size * 5
        self.maze_surface = pygame.Surface(
            (
                self.block_size * block_count + self.wall_size,
                self.block_size * block_count + self.wall_size,
            ),
            depth=8,
        )
        player = Player()
        self.ball = pygame.transform.scale(
            player.picture,
            (self.block_size - self.wall_size, self.block_size - self.wall_size),
        )
        self.win_ball = pygame.transform.scale(
            player.win_picture,
            (self.block_size - self.wall_size, self.block_size - self.wall_size),
        )
        self.position = None
        self.update_rects = None
        self.last_drawn_ball = None

    def trail(self):
        drawrect = pygame.Rect(
            self.position[0] * self.block_size + 2 * self.wall_size,
            self.position[1] * self.block_size + 2 * self.wall_size,
            self.wall_size,
            self.wall_size,
        )
        pygame.draw.rect(self.maze_surface, (255, 255, 255), drawrect)

    def set_position(self, n_position):
        self.position = n_position
        if self.last_drawn_ball is not None:
            self.update_maze_surface(self.last_drawn_ball)
            self.last_drawn_ball = None

    def erase(self):
        self.maze_surface.fill((0, 0, 0))
        self.screen.fill((0, 0, 0))
        pygame.display.update()

    def update_maze_surface(self, rect):
        self.screen.blit(self.maze_surface, rect, rect)
        self.redraw_rect(rect)

    def redraw_rect(self, rect):
        if self.update_rects is None:
            self.update_rects = [rect]
        else:
            self.update_rects.append(rect)

    @property
    def won(self):
        return (
            self.position is not None
            and self.position[0] == self.block_count - 1
            and self.position[1] == self.block_count - 1
        )

    def update(self):
        if self.position is not None and self.last_drawn_ball is None:
            self.last_drawn_ball = pygame.Rect(
                self.position[0] * self.block_size + self.wall_size,
                self.position[1] * self.block_size + self.wall_size,
                self.block_size - self.wall_size,
                self.block_size - self.wall_size,
            )
            draw_ball = self.ball
            if self.won:
                draw_ball = self.win_ball
            self.screen.blit(draw_ball, self.last_drawn_ball)
            self.redraw_rect(self.last_drawn_ball)
        pygame.display.update(self.update_rects)
        self.update_rects = None


class Controller:
    def __init__(self, screen):
        self.screen = screen
        self.joystick = None
        if pygame.joystick.get_count() >= 1:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        self.done = False
        self.set_level(DIFFICULTY)

    def set_level(self, level):
        self.level = level
        self.view = View(self.screen, self.level)

    def quit_handler(self, event):
        self.done = True

    def joybuttondown_handler(self, event):
        if event.button is BUTTON_START:
            self.done = True

    def joymotion_handler(self, event):
        if event.axis >= 2:
            return
        direction = None
        if event.value < 0:
            direction = maze.Maze.BACKWARD
        elif event.value > 0:
            direction = maze.Maze.FORWARD
        else:
            return
        self.move_player(event.axis, direction)

    def key_handler(self, event):
        direction = {
            KEYUP: (1, maze.Maze.BACKWARD),
            KEYDOWN: (1, maze.Maze.FORWARD),
            KEYLEFT: (0, maze.Maze.BACKWARD),
            KEYRIGHT: (0, maze.Maze.FORWARD),
        }.get(event.scancode, None)
        if direction:
            self.move_player(*direction)

    def move_player(self, axis, direction):
        try:
            n_position = self.maze.walk(self.view.position, axis, direction)
            self.view.trail()
            self.view.set_position(n_position)
        except Exception:
            pass

    def set_maze(self, maze):
        self.maze = maze
        self.view.set_position([0, 0])

    def run(self):
        generation = DrawMazeGeneration(self)
        handlers = {
            pygame.QUIT: self.quit_handler,
            pygame.JOYBUTTONDOWN: self.joybuttondown_handler,
            pygame.JOYAXISMOTION: self.joymotion_handler,
            pygame.KEYDOWN: self.key_handler,
        }
        every = 0
        while not self.done:
            if generation:
                try:
                    next(generation)
                except StopIteration:
                    generation = generation.next_phase()
            elif self.view.won:
                self.view.erase()
                self.set_level(self.level + 1)
                generation = DrawMazeGeneration(self)

            for event in pygame.event.get():
                h = handlers.get(event.type)
                if h:
                    h(event)
            if generation is None or every == 0:
                self.view.update()
                every = 10
            else:
                every -= 1


def main():
    pygame.init()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w - 100, info.current_h - 100))
    del info
    rval = 0
    g = Controller(screen)
    g.run()
    del g
    pygame.quit()
    return rval


if __name__ == "__main__":
    sys.exit(main())
