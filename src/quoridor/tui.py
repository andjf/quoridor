import os
from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from dataclasses import dataclass

from quoridor.constants import BOARD_SIZE
from quoridor.engine import QuoridorBot, QuoridorState
from quoridor.model_types import Move, MoveType, Orientation, Player, Vector


@dataclass
class RenderConfig:
    cell_width: int = 3  # number of chars inside each cell
    horiz_seg: str = "-"
    horiz_wall_seg: str = "═"
    vert_seg: str = "│"
    vert_wall_seg: str = "║"
    empty_cell: str = "   "
    light_mark: str = " L "
    dark_mark: str = " D "
    show_coords: bool = True
    colors: bool = True  # whether to colorize ANSI output


# Simple ANSI fallback colors
class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def parse_coordinate(coord: str) -> tuple[int, int]:
    col_char = coord[0].lower()
    row_char = coord[1:]
    col = ord(col_char) - ord("a")
    row = 9 - int(row_char)
    return row, col


def format_coordinate(vec: Vector) -> str:
    col_char = chr(vec.y + ord("a"))
    row_char = str(9 - vec.x)
    return f"{col_char}{row_char}"


def parse_input(input_str: str) -> Move | None:
    input_str = input_str.strip().lower()
    if not input_str:
        return None
    try:
        is_wall = False
        orient = None
        if input_str.endswith("h"):
            is_wall = True
            orient = Orientation.HORIZONTAL
            coord_part = input_str[:-1]
        elif input_str.endswith("v"):
            is_wall = True
            orient = Orientation.VERTICAL
            coord_part = input_str[:-1]
        else:
            coord_part = input_str
        r, c = parse_coordinate(coord_part)
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return None
        pos = Vector(r, c)
        if is_wall:
            return (MoveType.WALL, (pos, orient))
        else:
            return (MoveType.MOVE, pos)
    except (ValueError, IndexError):
        return None


def _joint_char(has_up, has_down, has_left, has_right):
    # box-drawing selection based on neighboring segments
    if has_up and has_down and has_left and has_right:
        return "┼"
    if has_up and has_down and has_left:
        return "┤"
    if has_up and has_down and has_right:
        return "├"
    if has_left and has_right and has_down:
        return "┬"
    if has_left and has_right and has_up:
        return "┴"
    if has_down and has_right:
        return "┌"
    if has_down and has_left:
        return "┐"
    if has_up and has_right:
        return "└"
    if has_up and has_left:
        return "┘"
    if has_left and has_right:
        return "-"
    if has_up and has_down:
        return "│"
    if has_left:
        return "-"
    if has_right:
        return "-"
    if has_up:
        return "│"
    if has_down:
        return "│"
    return "+"


def render_board(state: QuoridorState, cfg: RenderConfig | None) -> None:
    """
    Render using a character buffer. Supports optional rich Console.
    The visual grid dimensions:
      display_rows = BOARD_SIZE * 2 + 1
      display_cols = BOARD_SIZE * (cell_width + 1) + 1
    Joints are at (jr*2, jc*(cell_width + 1))
    Cell centers at (r*2+1, c*(cell_width+1) + cell_width//2 + 1)
    """
    cfg = cfg or RenderConfig()

    rows = BOARD_SIZE * 2 + 1
    cols = BOARD_SIZE * (cfg.cell_width + 1) + 1

    # initialize buffer with spaces
    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    # fill default grid (separators)
    for jr in range(BOARD_SIZE + 1):
        for jc in range(BOARD_SIZE + 1):
            r = jr * 2
            c = jc * (cfg.cell_width + 1)
            grid[r][c] = "+"  # will be replaced with better joint later

    # fill default horizontal separators (between joints) with '-'
    for jr in range(0, rows, 2):
        for jc in range(0, cols):
            if grid[jr][jc] == " ":
                grid[jr][jc] = cfg.horiz_seg

    # fill default vertical separators
    for r in range(rows):
        for jc in range(0, cols, cfg.cell_width + 1):
            if grid[r][jc] == " ":
                grid[r][jc] = cfg.vert_seg

    # fill empty cell interiors
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            center_r = r * 2 + 1
            start_c = c * (cfg.cell_width + 1) + 1
            for offset in range(cfg.cell_width):
                grid[center_r][start_c + offset] = " "

    # overlay walls from state.walls
    # Horizontal walls: anchored at (r,c) and cover two segments (c and c+1)
    for (wr, wc), orient in state.walls:
        if orient == Orientation.HORIZONTAL:
            # place wall across two cell-columns: segments at s = wc and s = wc + 1
            sep_row = (wr + 1) * 2  # between row wr and wr+1
            for seg in (wc, wc + 1):
                if 0 <= seg < BOARD_SIZE:
                    seg_start = seg * (cfg.cell_width + 1) + 1
                    for x in range(cfg.cell_width):
                        grid[sep_row][seg_start + x] = cfg.horiz_wall_seg
        else:  # VERTICAL
            # vertical walls anchored at (wr,wc) occupy two cell-rows: r and r+1
            sep_col = (wc + 1) * (cfg.cell_width + 1)
            for seg in (wr, wr + 1):
                if 0 <= seg < BOARD_SIZE:
                    row_center = seg * 2 + 1
                    grid[row_center][sep_col] = cfg.vert_wall_seg

    # compute and set joint characters using neighboring wall segments
    for jr in range(BOARD_SIZE + 1):
        for jc in range(BOARD_SIZE + 1):
            r = jr * 2
            c = jc * (cfg.cell_width + 1)
            has_left = False
            has_right = False
            has_up = False
            has_down = False

            # left segment exists if char immediately left (if valid) is horiz_wall_seg
            if c - 1 >= 0 and grid[r][c - 1] == cfg.horiz_wall_seg:
                has_left = True
            # right
            if c + 1 < cols and grid[r][c + 1] == cfg.horiz_wall_seg:
                has_right = True
            # up (check one row up)
            if r - 1 >= 0 and grid[r - 1][c] == cfg.vert_wall_seg:
                has_up = True
            # down
            if r + 1 < rows and grid[r + 1][c] == cfg.vert_wall_seg:
                has_down = True

            grid[r][c] = _joint_char(has_up, has_down, has_left, has_right)

    # place players at centers
    def place_mark(r: int, c: int, mark: str):
        cr = r * 2 + 1
        cc = c * (cfg.cell_width + 1) + (cfg.cell_width // 2) + 1
        # ensure mark fits into cell_width; if not, truncate/pad
        mm = mark
        if len(mm) > cfg.cell_width:
            mm = mm[: cfg.cell_width]
        pad = (cfg.cell_width - len(mm)) // 2
        for i, ch in enumerate(f"{' ' * pad}{mm}{' ' * (cfg.cell_width - pad - len(mm))}"):
            grid[cr][cc - (cfg.cell_width // 2) + i] = ch

    # state.light_pos and dark_pos are likely Vector or tuples; handle both
    lp = state.light_pos
    dp = state.dark_pos
    if isinstance(lp, tuple):
        place_mark(lp[0], lp[1], cfg.light_mark.strip())
    else:
        place_mark(lp.x, lp.y, cfg.light_mark.strip())

    if isinstance(dp, tuple):
        place_mark(dp[0], dp[1], cfg.dark_mark.strip())
    else:
        place_mark(dp.x, dp.y, cfg.dark_mark.strip())

    # produce string lines, optionally colorize players/walls using ANSI
    lines = ["".join(row) for row in grid]

    if cfg.show_coords:
        # add top/bottom coordinate row
        coord_row = " " * 2
        for c in range(BOARD_SIZE):
            mid = c * (cfg.cell_width + 1) + (cfg.cell_width // 2) + 1
            # place column letter centered in cell width
            coord_row = coord_row[:mid] + (" " * max(0, mid - len(coord_row))) + chr(ord("a") + c)
        # place row numbers on each side
        # We'll print coord row above the board
        pass  # we'll add coords in final output below

    # ANSI or plain text
    out = []
    if cfg.show_coords:
        header_cols = []
        for i in range(BOARD_SIZE):
            header_cols.append(f"{chr(ord('a') + i):^{cfg.cell_width + 1}}")
        out.append("  " + "".join(header_cols))
    for i, line in enumerate(lines):
        if cfg.show_coords and i % 2 == 1:
            row_num = str(9 - (i // 2))
            out.append(f"{row_num} {line} {row_num}")
        else:
            if cfg.show_coords:
                out.append("  " + line)
            else:
                out.append(line)
    if cfg.show_coords:
        footer_cols = []
        for i in range(BOARD_SIZE):
            footer_cols.append(f"{chr(ord('a') + i):^{cfg.cell_width + 1}}")
        out.append("  " + "".join(footer_cols))
    # apply simple ANSI colorization if requested
    if cfg.colors:
        colored = []
        for line in out:
            line = line.replace(cfg.horiz_wall_seg, f"{Ansi.YELLOW}{cfg.horiz_wall_seg}{Ansi.RESET}")
            line = line.replace(cfg.vert_wall_seg, f"{Ansi.YELLOW}{cfg.vert_wall_seg}{Ansi.RESET}")
            line = line.replace("L", f"{Ansi.BLUE}{Ansi.BOLD}L{Ansi.RESET}")
            line = line.replace("D", f"{Ansi.RED}{Ansi.BOLD}D{Ansi.RESET}")
            colored.append(line)
        out = colored

    print("\n".join(out))

    print()
    if cfg.colors:
        print(
            f"{Ansi.BLUE}Light Walls: {state.light_walls_left}{Ansi.RESET} | {Ansi.RED}Dark Walls: {state.dark_walls_left}{Ansi.RESET}"
        )


def main(depth: int = 2, colors: bool = True):
    game = QuoridorState()
    bot = QuoridorBot(depth=depth)

    cfg = RenderConfig(colors=colors)

    print("Welcome to Quoridor TUI!")
    print("Instructions:")
    print(" - Move: Type coordinate (e.g., 'e2')")
    print(" - Wall: Type coordinate + orientation (e.g., 'e2h' or 'e2v')")
    print("   (Walls are placed below (h) or to the right (v) of the coordinate)")
    input("Press Enter to start...")

    while True:
        clear_screen()
        render_board(game, cfg)

        winner = game.check_winner()
        if winner:
            print(f"\nGAME OVER! {winner.name} wins!")
            break

        if game.turn == Player.LIGHT:
            raw = input("\nYour Move (L) > ")
            if raw.lower() in ["q", "quit", "exit"]:
                break

            move = parse_input(raw)
            if not move:
                print("Invalid format. Use 'e2', 'e2h', or 'e2v'.")
                input("Press Enter...")
                continue

            legal_moves = game.get_legal_moves()
            if move not in legal_moves:
                print("Illegal move! Path blocked, wall overlaps, or out of bounds.")
                input("Press Enter...")
                continue

            game = game.apply_move(move)
        else:
            print("\nDark (Bot) is thinking...")
            best_move = bot.get_best_move(game, Player.DARK)
            if best_move:
                m_type, data = best_move
                if m_type == MoveType.MOVE:
                    print(f"Bot moves to {format_coordinate(data)}")
                else:
                    pos, orient = data
                    print(f"Bot places wall at {format_coordinate(pos)}{orient}")
                game = game.apply_move(best_move)
            else:
                print("Bot has no moves! (This shouldn't happen)")
                break


def get_args() -> Namespace:
    parser = ArgumentParser(description="Quoridor TUI")
    parser.add_argument("--colors", action=BooleanOptionalAction, default=True, help="Enable ANSI color output")
    parser.add_argument("--depth", type=int, default=2, help="Set the bot depth")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    main(depth=args.depth, colors=args.colors)
