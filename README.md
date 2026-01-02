# Quoridor Engine

A competitive AI agent for the abstract strategy game **Quoridor**, implemented in Python. This bot uses adversarial search and graph theory to outmaneuver opponents in a race across a $9 \times 9$ grid.

## 🧠 The Algorithm
Quoridor is computationally challenging because players can place walls to dynamically change the "map" of the game. This engine uses:

* **Minimax with Alpha-Beta Pruning:** Searches the game tree to a configurable depth, discarding "dead" branches to save processing time.
* **A\* (A-Star) Pathfinding:** Used within the heuristic function to calculate the exact distance to the goal for both players.
* **Heuristic Evaluation:** The bot calculates board favorability using the formula:  
    $$Score = \text{Dist}(\text{Opponent}) - \text{Dist}(\text{Self})$$
* **Path Validation:** Ensures every move complies with the "Golden Rule" (never completely blocking a player's path to the goal).

## 🚀 Features
- **Efficient Move Generation:** Prioritizes pawn jumps and strategic wall placements to optimize the search space.
- **Dynamic Maze Navigation:** Automatically adapts to complex corridor structures created by the opponent.
- **Customizable Depth:** Easily adjust the "intelligence" level by changing the look-ahead depth.

## 🛠️ Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/quoridor-ai.git](https://github.com/your-username/quoridor-ai.git)
   cd quoridor-ai