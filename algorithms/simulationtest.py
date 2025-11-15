"""
Interactive, step-by-step simulation harness for debugging Sphero swarm algorithms.

This module mirrors the rendering logic used in `simulation.py`, but replaces the
continuous automatic loop with a developer-controlled workflow:

* Each bonded group receives an explicit direction from the user.
* The simulation advances exactly one time step per user trigger.
* After every move we recompute bonding information and present detailed logs.

Run with: `python -m algorithms.simulationtest`
"""

from __future__ import annotations

import pathlib
import sys
from typing import Dict, List, Optional, Tuple

import pygame


current_file = pathlib.Path(__file__).resolve()
package_root = current_file.parent.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from algorithms.sphero import LinkedSphero
from algorithms.simulation import moving_sphero_to_target


# ---------------------------------------------------------------------------
# Grid drawing helpers
# ---------------------------------------------------------------------------


def draw_test_grid(surface: pygame.Surface) -> None:
    """
    Draw a grid that mirrors the layout used by `algorithms.simulation.draw_grid`.

    We reference the grid configuration constants explicitly for clarity, while
    keeping the rendered appearance identical to the production simulation.
    """

    # Vertical lines
    for col in range(GRID_WIDTH):
        x = col * SIM_DIST
        pygame.draw.line(surface, BLACK, (x, 0), (x, SIM_HEIGHT))

    # Horizontal lines
    for row in range(GRID_HEIGHT):
        y = row * SIM_DIST
        pygame.draw.line(surface, BLACK, (0, y), (SIM_WIDTH, y))

    # Diagonal crosshatch per cell
    for col in range(GRID_WIDTH - 1):
        for row in range(GRID_HEIGHT - 1):
            x = col * SIM_DIST
            y = row * SIM_DIST
            pygame.draw.line(surface, BLACK, (x, y), (x + SIM_DIST, y + SIM_DIST))
            pygame.draw.line(surface, BLACK, (x + SIM_DIST, y), (x, y + SIM_DIST))

# Mapping for human-readable direction names that matches the existing driver.
DIRECTION_LABELS: Dict[int, str] = {
    0: "Stay",
    1: "Up",
    2: "Up-Right",
    3: "Right",
    4: "Down-Right",
    5: "Down",
    6: "Down-Left",
    7: "Left",
    8: "Up-Left",
}


KEY_TO_DIRECTION = {
    pygame.K_0: 0,
    pygame.K_1: 1,
    pygame.K_2: 2,
    pygame.K_3: 3,
    pygame.K_4: 4,
    pygame.K_5: 5,
    pygame.K_6: 6,
    pygame.K_7: 7,
    pygame.K_8: 8,
    pygame.K_KP0: 0,
    pygame.K_KP1: 1,
    pygame.K_KP2: 2,
    pygame.K_KP3: 3,
    pygame.K_KP4: 4,
    pygame.K_KP5: 5,
    pygame.K_KP6: 6,
    pygame.K_KP7: 7,
    pygame.K_KP8: 8,
}

USER_TO_ALGO_DIRECTION = {
    0: 0,  # Stay
    1: 5,  # Up
    2: 4,  # Up-Right
    3: 3,  # Right
    4: 2,  # Down-Right
    5: 1,  # Down
    6: 8,  # Down-Left
    7: 7,  # Left
    8: 6,  # Up-Left
}


class StepSimulationTest:
    """
    Pygame-driven UI that advances the swarm algorithms one time-step at a time.

    The object owns both the underlying algorithm state and the rendered
    `LinkedSphero` instances. Each loop iteration:

    1. Waits for the user to press Space to begin a new step.
    2. Prompts for a single direction per bonding group (keys 0-8).
    3. Animates the movement towards the user-specified targets.
    4. Updates bonding groups and prints a structured summary.
    """

    def __init__(
        self,
        grid_width: int = GRID_WIDTH,
        grid_height: int = GRID_HEIGHT,
        initial_positions: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("sphero-swarm simulation (step-by-step)")
        self.grid_margin = (20, 20)
        self.panel_spacing = 20
        self.margin_right = 20
        self.margin_bottom = 20
        self.min_info_width = 260
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.sim_surface = pygame.Surface((SIM_WIDTH, SIM_HEIGHT))
        self.surface: pygame.Surface = pygame.display.set_mode((1, 1))
        self.info_surface: pygame.Surface = pygame.Surface((1, 1))
        self.window_width = 1
        self.window_height = 1
        self.info_panel_width = self.min_info_width
        self.info_offset = (self.grid_margin[0] + SIM_WIDTH + self.panel_spacing, self.grid_margin[1])
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 20)
        self.font_id = pygame.font.Font(None, 22)
        self.line_height = self.font_small.get_linesize()

        converted_initial_positions = None
        if initial_positions:
            converted_initial_positions = [
                self._display_to_algo_point(pos) for pos in initial_positions
            ]

        self.algorithm = Algorithm(
            grid_width=grid_width,
            grid_height=grid_height,
            n_spheros=N_SPHEROS,
            initial_positions=converted_initial_positions,
        )
        self.linked_spheros: List[LinkedSphero] = [
            LinkedSphero(sphero) for sphero in self.algorithm.spheros
        ]

        self.running = True
        self.mode: str = "idle"  # idle -> collecting -> animating
        self.step_counter = 0
        self.pending_step_number = 1
        self.active_groups: List[Dict[str, object]] = []
        self.current_group_index = 0
        self.error_message: Optional[str] = None
        self.status_message: str = "Press SPACE to start the first step."
        self.reserved_targets: Dict[Tuple[int, int], str] = {}

        self._log_initial_state()
        initial_overlay = self._collect_overlay_lines()
        self._layout_surfaces(initial_overlay)

    def _algo_to_display_coords(self, x: float, y: float) -> Tuple[float, float]:
        return x, (self.grid_height - 1) - y
    
    def _display_to_algo_point(self, point: Tuple[int, int]) -> Tuple[int, int]:
        x, y = point
        if not (0 <= x < self.grid_width) or not (0 <= y < self.grid_height):
            raise ValueError(
                f"Initial position {point} is out of bounds for a {self.grid_width}x{self.grid_height} grid."
            )
        algo_y = self.grid_height - 1 - y
        return int(x), int(algo_y)

    def _layout_surfaces(self, overlay_lines: List[str]) -> None:
        """
        Compute dynamic window and info-panel sizing based on grid dimensions and
        current overlay content.
        """

        text_width = max((self.font_small.size(line)[0] for line in overlay_lines), default=0)
        info_width = max(self.min_info_width, text_width + 20)
        overlay_height = len(overlay_lines) * self.line_height + 24  # padding

        margin_left, margin_top = self.grid_margin
        total_width = margin_left + SIM_WIDTH + self.panel_spacing + info_width + self.margin_right
        total_height = max(
            margin_top + SIM_HEIGHT + self.margin_bottom,
            margin_top + overlay_height + self.margin_bottom,
        )

        if (
            total_width != self.window_width
            or total_height != self.window_height
            or info_width != self.info_panel_width
        ):
            self.window_width = total_width
            self.window_height = total_height
            self.info_panel_width = info_width
            self.surface = pygame.display.set_mode((self.window_width, self.window_height))
            info_height = self.window_height - margin_top - self.margin_bottom
            self.info_surface = pygame.Surface((self.info_panel_width, info_height))
            pygame.display.set_caption("sphero-swarm simulation (step-by-step)")

        self.info_offset = (margin_left + SIM_WIDTH + self.panel_spacing, margin_top)

    def run(self) -> None:
        """Main event loop."""
        while self.running:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(60)
        pygame.quit()

    # ------------------------------------------------------------------
    # Event handling & state transitions
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.mode == "idle" and event.key == pygame.K_SPACE:
                    self._begin_direction_collection()
                elif self.mode == "collecting":
                    if event.key in KEY_TO_DIRECTION:
                        self._handle_direction_input(KEY_TO_DIRECTION[event.key])
                    elif event.key == pygame.K_BACKSPACE:
                        self._rewind_group_selection()

    def _update(self) -> None:
        if self.mode == "animating":
            self._animate_step()

    # ------------------------------------------------------------------
    # Direction selection helpers
    # ------------------------------------------------------------------

    def _begin_direction_collection(self) -> None:
        self.pending_step_number = self.step_counter + 1
        self.active_groups = self._compute_active_groups()
        self.current_group_index = 0
        self.mode = "collecting"
        self.error_message = None
        self.status_message = (
            "Selecting directions: use number keys 0-8. Backspace to edit."
        )
        self.reserved_targets.clear()

        self._log_step_header()

    def _handle_direction_input(self, direction: int) -> None:
        group = self.active_groups[self.current_group_index]
        members: List[int] = group["members"]  # type: ignore[assignment]

        algo_direction = USER_TO_ALGO_DIRECTION[direction]

        if not self._is_direction_valid(members, algo_direction):
            group_label = group["label"]
            direction_name = DIRECTION_LABELS[direction]
            self.error_message = (
                f"{group_label}: direction {direction} ({direction_name}) is invalid."
            )
            return

        group_label = group["label"]
        targets: List[Tuple[int, int]] = []
        for sphero_id in members:
            sphero = self.algorithm.find_sphero(sphero_id)
            if sphero is None:
                continue
            target_pos = sphero.compute_target_position(algo_direction)
            reserved_by = self.reserved_targets.get(target_pos)
            if reserved_by and reserved_by != group_label:
                display_target = self._algo_to_display_coords(*target_pos)
                self.error_message = (
                    f"{group_label}: target {display_target} already reserved by {reserved_by}."
                )
                return
            targets.append(target_pos)

        # Release any previously stored targets for this group before reassigning.
        previous_targets: List[Tuple[int, int]] = group.get("targets", [])  # type: ignore[assignment]
        for target in previous_targets:
            self.reserved_targets.pop(target, None)

        for target in targets:
            self.reserved_targets[target] = group_label
        group["targets"] = targets
        group["user_direction"] = direction
        group["algo_direction"] = algo_direction
        self.error_message = None
        self.status_message = (
            f"{group_label} -> {direction} ({DIRECTION_LABELS[direction]})."
        )
        print(f"{group_label} direction set to {direction} ({DIRECTION_LABELS[direction]}).")

        self.current_group_index += 1
        if self.current_group_index >= len(self.active_groups):
            self._commit_step()
        else:
            next_group = self.active_groups[self.current_group_index]
            self.status_message += (
                f" Next: {next_group['label']} (members {next_group['members']})."
            )

    def _rewind_group_selection(self) -> None:
        if self.current_group_index == 0:
            return
        self.current_group_index -= 1
        group = self.active_groups[self.current_group_index]
        group["user_direction"] = None
        group["algo_direction"] = None
        previous_targets: List[Tuple[int, int]] = group.get("targets", [])  # type: ignore[assignment]
        for target in previous_targets:
            self.reserved_targets.pop(target, None)
        group["targets"] = []
        self.status_message = (
            f"Re-enter direction for {group['label']} (members {group['members']})."
        )

    def _is_direction_valid(self, members: List[int], algo_direction: int) -> bool:
        if algo_direction not in USER_TO_ALGO_DIRECTION.values():
            return False
        for sphero_id in members:
            sphero = self.algorithm.find_sphero(sphero_id)
            if sphero is None or not self.algorithm.is_valid_move(algo_direction, sphero):
                return False
        return True

    def _commit_step(self) -> None:
        self.mode = "animating"
        self.error_message = None
        self.status_message = f"Animating step {self.pending_step_number}..."

        for group in self.active_groups:
            algo_direction = group.get("algo_direction")
            if algo_direction is None:
                continue
            members: List[int] = group["members"]  # type: ignore[assignment]
            for sphero_id in members:
                sphero = self.algorithm.find_sphero(sphero_id)
                if sphero is None:
                    continue
                sphero.update_movement(algo_direction)

        for group in self.active_groups:
            algo_direction = group.get("algo_direction")
            if algo_direction is None:
                continue
            members = group["members"]  # type: ignore[assignment]
            for sphero_id in members:
                sphero = self.algorithm.find_sphero(sphero_id)
                if sphero is None:
                    continue
                self.algorithm.update_nodes(sphero)

        print("Directions committed. Animating towards targets...")
        self.reserved_targets.clear()

    # ------------------------------------------------------------------
    # Animation & post-step accounting
    # ------------------------------------------------------------------

    def _animate_step(self) -> None:
        animating = False
        for linked in self.linked_spheros:
            if moving_sphero_to_target(linked):
                animating = True
        if not animating:
            self._finalize_step()

    def _finalize_step(self) -> None:
        for sphero in self.algorithm.spheros:
            sphero.x = sphero.target_x
            sphero.y = sphero.target_y

        for linked in self.linked_spheros:
            linked.x = linked.sphero.x
            linked.y = linked.sphero.y

        self.algorithm.update_grid_bonds()

        self.step_counter = self.pending_step_number
        self.mode = "idle"
        self.status_message = (
            f"Step {self.step_counter} complete. Press SPACE to continue."
        )
        self._log_step_summary()

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render(self) -> None:
        overlay_lines = self._collect_overlay_lines()
        self._layout_surfaces(overlay_lines)

        self.surface.fill((230, 230, 230))
        self.sim_surface.fill(WHITE)
        draw_test_grid(self.sim_surface)
        for linked in self.linked_spheros:
            self._draw_sphero_circle(linked)
            self._draw_sphero_label(linked)
        self.surface.blit(self.sim_surface, self.grid_margin)
        self._draw_overlay(overlay_lines)
        pygame.display.flip()

    def _draw_sphero_circle(self, sphero: LinkedSphero) -> None:
        display_x, display_y = self._algo_to_display_coords(sphero.x, sphero.y)
        center_x = int(round(display_x * SIM_DIST))
        center_y = int(round(display_y * SIM_DIST))
        pygame.draw.circle(self.sim_surface, sphero.color, (center_x, center_y), SPHERO_SIM_RADIUS)

    def _draw_sphero_label(self, sphero: LinkedSphero) -> None:
        display_x, display_y = self._algo_to_display_coords(sphero.x, sphero.y)
        label_surface = self.font_id.render(str(sphero.id), True, BLACK)
        center_x = int(round(display_x * SIM_DIST))
        center_y = int(round(display_y * SIM_DIST))
        label_rect = label_surface.get_rect(center=(center_x, center_y))
        self.sim_surface.blit(label_surface, label_rect)

    def _collect_overlay_lines(self) -> List[str]:
        lines: List[str] = [
            f"Mode: {self.mode.upper()}",
            f"Completed steps: {self.step_counter}",
            self.status_message,
        ]

        if self.error_message:
            lines.append(f"Error: {self.error_message}")

        if self.mode == "collecting" and self.active_groups:
            current = self.active_groups[self.current_group_index]
            lines.append(
                f"Selecting {current['label']} (members {current['members']})."
            )
            groups = self.active_groups
        else:
            groups = (
                self._compute_active_groups()
                if self.mode == "idle"
                else self.active_groups
            )

        lines.append("Bonding groups:")
        for group in groups:
            user_direction = group.get("user_direction")
            direction_note = (
                f"{user_direction} ({DIRECTION_LABELS.get(user_direction, '-')})"
                if user_direction is not None
                else "-"
            )
            lines.append(
                f"  {group['label']}: {group['members']} | dir: {direction_note}"
            )

        lines.append("Positions (current -> target):")
        for linked in self.linked_spheros:
            disp_x, disp_y = self._algo_to_display_coords(linked.x, linked.y)
            target_disp_x, target_disp_y = self._algo_to_display_coords(
                linked.target_x, linked.target_y
            )
            lines.append(
                f"  S{linked.id}: ({disp_x:.2f}, {disp_y:.2f}) -> ({target_disp_x:.0f}, {target_disp_y:.0f})"
            )

        return lines

    def _draw_overlay(self, overlay_lines: List[str]) -> None:
        self.info_surface.fill((245, 245, 245))
        y_offset = 12
        for line in overlay_lines:
            color = (220, 0, 0) if line.startswith("Error") else (0, 0, 0)
            text_surface = self.font_small.render(line, True, color)
            self.info_surface.blit(text_surface, (10, y_offset))
            y_offset += self.line_height

        self.surface.blit(self.info_surface, self.info_offset)

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_initial_state(self) -> None:
        print("=== Step 0 (Initial State) ===")
        self._print_positions()
        self._print_groups(self._compute_active_groups())

    def _log_step_header(self) -> None:
        print(f"\n=== Step {self.pending_step_number} ===")
        self._print_positions()
        self._print_groups(self.active_groups)
        print("Enter one direction per group (keys 0-8).")

    def _log_step_summary(self) -> None:
        print(f"\nStep {self.step_counter} complete.")
        self._print_positions()
        self._print_groups(self._compute_active_groups())

    def _print_positions(self) -> None:
        print("Current positions:")
        for sphero in self.algorithm.spheros:
            disp_x, disp_y = self._algo_to_display_coords(sphero.x, sphero.y)
            print(
                f"  S{sphero.id}: ({disp_x}, {disp_y}) direction={sphero.direction}"
            )

    def _print_groups(self, groups: List[Dict[str, object]]) -> None:
        print("Bonding groups:")
        for group in groups:
            user_direction = group.get("user_direction")
            label = group["label"]
            members = group["members"]
            direction_text = (
                f"{user_direction} ({DIRECTION_LABELS.get(user_direction, '-')})"
                if user_direction is not None
                else "-"
            )
            print(f"  {label}: {members} | dir: {direction_text}")

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _compute_active_groups(self) -> List[Dict[str, object]]:
        groups: List[Dict[str, object]] = []
        group_index = 1
        for bonded in self.algorithm.swarm.bonded_groups:
            if not bonded:
                continue
            groups.append(
                {
                    "label": f"BG{group_index}",
                    "members": list(bonded),
                    "user_direction": None,
                    "algo_direction": None,
                    "targets": [],
                }
            )
            group_index += 1
        return groups

    # ------------------------------------------------------------------
    # Entry point helpers
    # ------------------------------------------------------------------


def run_step_simulation_test(
    initial_positions = None,
) -> None:
    """
    Convenience wrapper to launch the step simulation UI.

    Keeping a named entry point makes it easy to import and run this tool from
    other scripts or REPL sessions.

    Args:
        initial_positions: Optional list of `(x, y)` tuples to seed the algorithm.
            When omitted, the algorithm falls back to its internal random placement.
    """
    StepSimulationTest(initial_positions=initial_positions).run()



if __name__ == "__main__":
    initial_positions = [(0, 0), (2, 0)]
    # run_step_simulation_test()
    run_step_simulation_test(initial_positions=initial_positions)

