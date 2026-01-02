import os

from quoridor.constants import BOARD_SIZE
from quoridor.engine import (
    QuoridorBot,
    QuoridorState,
)
from quoridor.model_types import (
    Move,
    MoveType,
    Orientation,
    Player,
    Vector,
)


class TermColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"  # Dark Player
    BLUE = "\033[94m"  # Light Player
    YELLOW = "\033[93m"  # Walls
    GREEN = "\033[92m"  # Grid/Coords


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def parse_coordinate(coord: str) -> tuple[int, int]:
    """Parses 'e2' into (row_idx, col_idx)."""
    col_char = coord[0].lower()
    row_char = coord[1:]

    col = ord(col_char) - ord("a")
    # Map row '9' (top) to index 0, row '1' (bottom) to index 8
    row = 9 - int(row_char)
    return row, col


def format_coordinate(vec: Vector) -> str:
    """Formats (row, col) back to 'e2'."""
    col_char = chr(vec.y + ord("a"))
    row_char = str(9 - vec.x)
    return f"{col_char}{row_char}"


def parse_input(input_str: str) -> Move | None:
    """Parses 'e2' (move) or 'e2h' (horizontal wall)."""
    input_str = input_str.strip().lower()
    if not input_str:
        return None

    try:
        # Check for wall suffix
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

        # Validation of bounds for parsing
        if not (0 <= r < 9 and 0 <= c < 9):
            return None

        pos = Vector(r, c)

        if is_wall:
            return (MoveType.WALL, (pos, orient))
        else:
            return (MoveType.MOVE, pos)

    except (ValueError, IndexError):
        return None


def render_board(state: QuoridorState):
    # Header
    print(f" {TermColors.GREEN}  a   b   c   d   e   f   g   h   i{TermColors.RESET}")
    print(f" {TermColors.GREEN}+---{'+---' * 8}{TermColors.RESET}")

    for r in range(BOARD_SIZE):
        # Row Content
        line_top = f"{TermColors.GREEN}{9 - r}|{TermColors.RESET}"

        for c in range(BOARD_SIZE):
            # 1. Determine Cell Content
            cell_str = "   "
            if state.light_pos == (r, c):
                cell_str = f" {TermColors.BLUE}{TermColors.BOLD}L{TermColors.RESET} "
            elif state.dark_pos == (r, c):
                cell_str = f" {TermColors.RED}{TermColors.BOLD}D{TermColors.RESET} "

            # 2. Determine Vertical Wall to the right
            # A vertical wall at (r, c) blocks (r,c) <-> (r, c+1)
            is_v_wall = ((r, c), Orientation.VERTICAL) in state.walls
            # Also check if it's the bottom half of a vertical wall starting at r-1
            is_v_wall_prev = ((r - 1, c), Orientation.VERTICAL) in state.walls

            separator = (
                f"{TermColors.YELLOW}┃{TermColors.RESET}"
                if (is_v_wall or is_v_wall_prev)
                else f"{TermColors.GREEN}|{TermColors.RESET}"
            )

            line_top += f"{cell_str}{separator}"

        print(line_top + f"{TermColors.GREEN}{9 - r}{TermColors.RESET}")

        # Row Separator (Horizontal Walls)
        if r < BOARD_SIZE - 1:
            line_sep = f" {TermColors.GREEN}+{TermColors.RESET}"
            for c in range(BOARD_SIZE):
                # A horizontal wall at (r, c) blocks (r,c) <-> (r+1, c)
                is_h_wall = ((r, c), Orientation.HORIZONTAL) in state.walls
                # Also check if it's the right half of a horizontal wall starting at c-1
                is_h_wall_prev = ((r, c - 1), Orientation.HORIZONTAL) in state.walls

                wall_char = (
                    f"{TermColors.YELLOW}==={TermColors.RESET}"
                    if (is_h_wall or is_h_wall_prev)
                    else f"{TermColors.GREEN}---{TermColors.RESET}"
                )
                corner = f"{TermColors.GREEN}+{TermColors.RESET}"

                line_sep += f"{wall_char}{corner}"
            print(line_sep)

    print(f" {TermColors.GREEN}+---{'+---' * 8}{TermColors.RESET}")
    print(f" {TermColors.GREEN}  a   b   c   d   e   f   g   h   i{TermColors.RESET}")
    print(
        f"\n{TermColors.BLUE}Light Walls: {state.light_walls_left}{TermColors.RESET} | {TermColors.RED}Dark Walls: {state.dark_walls_left}{TermColors.RESET}"
    )


def main():
    game = QuoridorState()
    bot = QuoridorBot(depth=2)  # Depth 2 is fast for Python; use 3 for harder bot

    print("Welcome to Quoridor TUI!")
    print("Instructions:")
    print(" - Move: Type coordinate (e.g., 'e2')")
    print(" - Wall: Type coordinate + orientation (e.g., 'e2h' or 'e2v')")
    print("   (Walls are placed below (h) or to the right (v) of the coordinate)")
    input("Press Enter to start...")

    while True:
        clear_screen()
        render_board(game)

        winner = game.check_winner()
        if winner:
            print(f"\nGAME OVER! {winner.name} wins!")
            break

        if game.turn == Player.LIGHT:
            # Human Turn
            raw = input(f"\n{TermColors.BLUE}Your Move (L) > {TermColors.RESET}")
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
            # Bot Turn
            print(f"\n{TermColors.RED}Dark (Bot) is thinking...{TermColors.RESET}")
            best_move = bot.get_best_move(game, Player.DARK)
            if best_move:
                m_type, data = best_move
                if m_type == MoveType.MOVE:
                    print(f"Bot moves to {format_coordinate(data)}")
                else:
                    pos, orient = data
                    print(f"Bot places wall at {format_coordinate(pos)}{orient}")
                game = game.apply_move(best_move)
                # Small pause to let user see bot's decision if desired
                # import time; time.sleep(1)
            else:
                print("Bot has no moves! (This shouldn't happen)")
                break


if __name__ == "__main__":
    main()
