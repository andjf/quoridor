from __future__ import annotations

from quoridor.constants import (
    BOT_DEPTH,
    INFINITY,
    WIN_SCORE,
)
from quoridor.model_types import (
    Move,
    MoveType,
    Player,
)
from quoridor.state import QuoridorState


class QuoridorBot:
    def __init__(self, depth: int = BOT_DEPTH) -> None:
        self.depth = depth

    def get_best_move(self, state: QuoridorState, player_id: Player) -> Move | None:
        _, best_move = self.minimax(
            state,
            self.depth,
            -INFINITY,
            INFINITY,
            True,
            player_id,
        )
        return best_move

    def minimax(
        self,
        state: QuoridorState,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        player_id: Player,
    ) -> tuple[float, Move | None]:
        winner = state.check_winner()
        if winner:
            return (WIN_SCORE + depth, None) if winner == player_id else (-WIN_SCORE - depth, None)
        if depth == 0:
            return self.evaluate(state, player_id), None

        legal_moves = state.get_legal_moves()
        # Optimization: Sort moves to prioritize pawn movement (better pruning usually)
        legal_moves.sort(key=lambda m: m[0] == MoveType.WALL)
        best_move = None

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
            return max_eval, best_move
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
            return min_eval, best_move

    def evaluate(self, state: QuoridorState, player_id: Player) -> int:
        my_dist = state.shortest_path_len(player_id)
        opp_dist = state.shortest_path_len(player_id.opponent)
        return opp_dist - my_dist
