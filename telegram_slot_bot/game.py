import random
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class SpinResult:
    grid: List[List[str]]  # 3x3
    lines: List[Tuple[int, List[str]]]  # (payout, symbols)
    total_win: int


class SlotMachine:
    def __init__(self) -> None:
        # Classic reel symbols with weights
        # Heavier weight = more common
        self.symbols = [
            ("🍒", 30, 5),   # pay 5 for 3 in a line
            ("🍋", 28, 8),   # 8
            ("🍇", 24, 10),  # 10
            ("🔔", 16, 15),  # 15
            ("💎", 10, 25),  # 25
            ("7️⃣", 6, 50),  # 50
            ("🌟", 8, 0),    # wild, own payout 0
        ]
        # Build weighted reel strip
        strip: List[str] = []
        for sym, weight, _ in self.symbols:
            strip.extend([sym] * weight)
        # Use same strip for 3 reels for a classic simple slot
        self.reels: List[List[str]] = [strip[:], strip[:], strip[:]]

    def _spin_reel(self, reel: List[str]) -> List[str]:
        # Pick a random start and take 3 consecutive symbols (wrap around)
        start = random.randrange(len(reel))
        return [reel[(start + i) % len(reel)] for i in range(3)]

    def spin(self) -> List[List[str]]:
        # Returns a 3x3 grid [rows][cols]
        cols = [self._spin_reel(reel) for reel in self.reels]
        # columns -> rows
        grid = [[cols[c][r] for c in range(3)] for r in range(3)]
        return grid

    def _is_wild(self, s: str) -> bool:
        return s == "🌟"

    def _line_payout(self, line: List[str], bet: int) -> Tuple[int, List[str]]:
        # Evaluate 3-symbol line with wilds. Wild substitutes to best match.
        a, b, c = line
        candidates = [s for s, _, _ in self.symbols if s != "🌟"]
        best_pay = 0
        best_syms = line
        for target in candidates:
            match = [target if self._is_wild(x) else x for x in line]
            if all(x == target for x in match):
                pay = self._payout_for_symbol(target) * bet
                if pay > best_pay:
                    best_pay = pay
                    best_syms = [target, target, target]
        return best_pay, best_syms

    def _payout_for_symbol(self, sym: str) -> int:
        for s, _w, pay in self.symbols:
            if s == sym:
                return pay
        return 0

    def evaluate(self, grid: List[List[str]], bet: int) -> SpinResult:
        # Lines: 3 horizontals + 2 diagonals
        lines_idx = [
            [(0, 0), (0, 1), (0, 2)],
            [(1, 0), (1, 1), (1, 2)],
            [(2, 0), (2, 1), (2, 2)],
            [(0, 0), (1, 1), (2, 2)],
            [(2, 0), (1, 1), (0, 2)],
        ]
        evaluated: List[Tuple[int, List[str]]] = []
        total = 0
        for coords in lines_idx:
            line = [grid[r][c] for r, c in coords]
            payout, matched = self._line_payout(line, bet)
            total += payout
            evaluated.append((payout, matched))
        return SpinResult(grid=grid, lines=evaluated, total_win=total)

    def play(self, bet: int) -> SpinResult:
        grid = self.spin()
        return self.evaluate(grid, bet)
