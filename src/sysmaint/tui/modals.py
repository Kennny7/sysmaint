# src/sysmaint/tui/modals.py

from __future__ import annotations

import json
from typing import Any

from rich.json import JSON as RichJSON
from rich.panel import Panel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RichLog, Static


class ElevationModal(ModalScreen[str]):
    """Prompt the user to restart with Administrator / root privileges before running a privileged task."""

    CSS = """
    ElevationModal {
        align: center middle;
    }
    #modal-box {
        width: 66;
        height: auto;
        background: $panel;
        border: round $warning;
        padding: 1 2;
    }
    #modal-title {
        color: $warning;
        text-style: bold;
        margin-bottom: 1;
    }
    #modal-body {
        margin-bottom: 1;
    }
    .modal-buttons {
        height: auto;
        align: right middle;
    }
    Button {
        margin-left: 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, action_name: str) -> None:
        super().__init__()
        self.action_name = action_name

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Administrator Privileges Required", id="modal-title")
            yield Static(
                f"'{self.action_name}' requires Administrator (Windows) or root/sudo (Linux) privileges.\n\n"
                "Running without elevation will fail with an access error.\n"
                "Would you like to restart SysMaint as Administrator now?",
                id="modal-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="btn-elev-cancel", variant="default")
                yield Button("Restart as Administrator", id="btn-elev-go", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-elev-go":
            self.dismiss("elevate")
        else:
            self.dismiss("cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class ConfirmLongTaskModal(ModalScreen[bool]):
    """Warn users before starting a long-running operation."""

    CSS = """
    ConfirmLongTaskModal {
        align: center middle;
    }
    #long-box {
        width: 68;
        height: auto;
        background: $panel;
        border: round $primary;
        padding: 1 2;
    }
    #long-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    #long-body {
        margin-bottom: 1;
    }
    .modal-buttons {
        height: auto;
        align: right middle;
    }
    Button {
        margin-left: 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, task_name: str, estimate: str, details: str) -> None:
        super().__init__()
        self.task_name = task_name
        self.estimate = estimate
        self.details = details

    def compose(self) -> ComposeResult:
        with Vertical(id="long-box"):
            yield Label(f"Start {self.task_name}?", id="long-title")
            yield Static(
                f"{self.details}\n\n"
                f"Estimated time: {self.estimate}\n\n"
                "Tip: You can minimize this window to the background while it runs. "
                "SysMaint will display live progress and real percentage updates as the command runs.",
                id="long-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="btn-long-cancel", variant="default")
                yield Button("Start Now", id="btn-long-start", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-long-start")

    def action_cancel(self) -> None:
        self.dismiss(False)


class TechnicalLogModal(ModalScreen[None]):
    """Full-window modal viewer for detailed technical logs and raw command output."""

    CSS = """
    TechnicalLogModal {
        align: center middle;
    }
    #log-window {
        width: 92%;
        height: 88%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    #log-header {
        height: auto;
        margin-bottom: 1;
    }
    #log-title {
        width: 1fr;
        color: $primary;
        text-style: bold;
    }
    #full-tech-log {
        height: 1fr;
        background: $background;
        border: round $panel;
        padding: 1;
    }
    Button {
        margin-left: 1;
    }
    """

    BINDINGS = [Binding("escape", "close_log", "Close")]

    def __init__(self, entries: list[tuple[str, Any]]) -> None:
        super().__init__()
        self.entries = entries

    def compose(self) -> ComposeResult:
        with Vertical(id="log-window"):
            with Horizontal(id="log-header"):
                yield Label("Technical Activity Log (Full View)", id="log-title")
                yield Button("Clear", id="btn-log-clear", variant="warning")
                yield Button("Close (Esc)", id="btn-log-close", variant="primary")
            yield RichLog(id="full-tech-log", wrap=True, highlight=True)

    def on_mount(self) -> None:
        log = self.query_one("#full-tech-log", RichLog)
        if not self.entries:
            log.write("No technical logs recorded yet. Run a scan or check to see full output here.")
            return
        for title, data in self.entries:
            log.write(Panel(RichJSON(json.dumps(data, default=str)), title=title, border_style="cyan"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-log-clear":
            self.entries.clear()
            self.query_one("#full-tech-log", RichLog).clear()
        else:
            self.dismiss(None)

    def action_close_log(self) -> None:
        self.dismiss(None)
