from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from quoridor.constants import BOT_DEPTH, INFINITY, WIN_SCORE
from quoridor.model_types import Move, MoveType, Player
from quoridor.state import QuoridorState


class QuoridorBot:
    def __init__(self, depth: int = BOT_DEPTH, use_multiprocessing: bool = True) -> None:
        self.depth = depth
        self.use_multiprocessing = use_multiprocessing
        # Transposition table: maps state_hash -> (score, depth, flag, best_move)
        # We use a dict for O(1) access.
        self.transposition_table = {}

    def get_best_move(self, state: QuoridorState, player_id: Player) -> Move | None:
        """
        Uses Iterative Deepening. It searches depth 1, then 2, then 3...
        This helps move ordering for the final deep search.
        """
        best_move = None

        # We clear the table between turns to prevent memory bloat,
        # though keeping it can help if memory permits.
        self.transposition_table.clear()

        # Iterative Deepening
        # If you have a time limit (e.g., 2 seconds), you can check time inside this loop
        for d in range(1, self.depth + 1):
            if d == self.depth and self.use_multiprocessing:
                # Run the final deepest search in parallel
                best_move = self.get_best_move_parallel(state, player_id, d)
            else:
                # Standard single-core search for shallow depths (fills TT for move ordering)
                _, best_move = self.minimax(state, d, -INFINITY, INFINITY, True, player_id)

        return best_move

    def get_best_move_parallel(self, state: QuoridorState, player_id: Player, depth: int) -> Move | None:
        """
        Root Parallelization: Distributes top-level moves across CPU cores.
        """
        legal_moves = self._get_ordered_moves(state)
        if not legal_moves:
            return None

        # Prepare arguments for each worker
        # We need to apply the move first because we can't share the 'state' object
        # mutably across processes easily.
        futures = []
        with ProcessPoolExecutor() as executor:
            for move in legal_moves:
                next_state = state.apply_move(move)
                # Submit the minimax task for this branch
                # Note: Workers won't share the Transposition Table, which is a trade-off
                futures.append(
                    executor.submit(
                        self._worker_minimax,
                        next_state,
                        depth - 1,
                        -INFINITY,
                        INFINITY,
                        False,
                        player_id,
                    )
                )

            # Collect results
            best_val = -INFINITY
            best_move = None

            for i, future in enumerate(futures):
                val = future.result()
                if val > best_val:
                    best_val = val
                    best_move = legal_moves[i]

        return best_move

    @staticmethod
    def _worker_minimax(state, depth, alpha, beta, maximizing, player_id):
        """
        Static helper for multiprocessing to avoid pickling the entire Bot instance.
        Creates a temporary bot for the worker process.
        """
        # Workers need their own bot instance or at least access to the logic
        # We create a lightweight bot just for the logic.
        bot = QuoridorBot(depth)
        val, _ = bot.minimax(state, depth, alpha, beta, maximizing, player_id)
        return val

    def minimax(
        self,
        state: QuoridorState,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        player_id: Player,
    ) -> tuple[float, Move | None]:
        # 1. Transposition Table Lookup
        # Assumes state can be stringified or hashed uniquely
        state_key = str(state)
        if state_key in self.transposition_table:
            tt_val, tt_depth, tt_flag, tt_move = self.transposition_table[state_key]
            # Use cached result if the stored depth is deeper or equal to current search
            if tt_depth >= depth:
                if tt_flag == "EXACT":
                    return tt_val, tt_move
                elif tt_flag == "LOWERBOUND":
                    alpha = max(alpha, tt_val)
                elif tt_flag == "UPPERBOUND":
                    beta = min(beta, tt_val)
                if alpha >= beta:
                    return tt_val, tt_move

        # 2. Base Case: Winner or Max Depth
        winner = state.check_winner()
        if winner:
            return (WIN_SCORE + depth, None) if winner == player_id else (-WIN_SCORE - depth, None)

        if depth == 0:
            return self.evaluate(state, player_id), None

        # 3. Move Generation & Ordering
        legal_moves = self._get_ordered_moves(state)

        best_move = None
        original_alpha = alpha

        if maximizing:
            max_eval = -INFINITY
            for move in legal_moves:
                new_state = state.apply_move(move)
                eval_score, _ = self.minimax(
                    new_state,
                    depth - 1,
                    alpha,
                    beta,
                    False,
                    player_id,
                )

                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move

                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break

            final_score = max_eval
        else:
            min_eval = INFINITY
            for move in legal_moves:
                new_state = state.apply_move(move)
                eval_score, _ = self.minimax(
                    new_state,
                    depth - 1,
                    alpha,
                    beta,
                    True,
                    player_id,
                )

                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move

                beta = min(beta, eval_score)
                if beta <= alpha:
                    break

            final_score = min_eval

        # 4. Store in Transposition Table
        tt_flag = "EXACT"
        if final_score <= original_alpha:
            tt_flag = "UPPERBOUND"
        elif final_score >= beta:
            tt_flag = "LOWERBOUND"

        self.transposition_table[state_key] = (final_score, depth, tt_flag, best_move)

        return final_score, best_move

    def _get_ordered_moves(self, state: QuoridorState) -> list[Move]:
        """
        Optimized move sorting.
        It is often better to try Pawn moves before Wall moves.
        """
        moves = state.get_legal_moves()
        # Heuristic: Pawn moves (False) before Wall moves (True)
        # Within Pawn moves, you might want to prioritize those that reduce distance to goal
        # but a simple sort is a good start.
        moves.sort(key=lambda m: m[0] == MoveType.WALL)
        return moves

    def evaluate(self, state: QuoridorState, player_id: Player) -> int:
        my_dist = state.shortest_path_len(player_id)
        opp_dist = state.shortest_path_len(player_id.opponent)
        return opp_dist - my_dist
