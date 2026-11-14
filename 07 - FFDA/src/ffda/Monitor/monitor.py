"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-46m
 * github: https://github.com/antsiri
 * copyright 2026

Log collection: filtering/classification engine and monitors that capture
error messages from a file (tail) or from a UDP syslog socket.
"""

import abc
import time
import re
import socket
from typing import Optional, Callable
from pathlib import Path


# ==========================================
# 1. FILTER ENGINE
# ==========================================

class LogFilterEngine:
    """
    Keeps only error messages, classifies them in a category and formats
    them as ``<timestamp_epoch> <node> <category> <message>``.
    """

    # Regex patterns (lower-case) that identify each error category
    CATEGORY_PATTERNS = {
        "DEV": [r"pci", r"device", r"hardware failure", r"bus failure"],
        "MEM": [r"ecc", r"ram", r"memory", r"dimm"],
        "I-O": [r"disk", r"storage", r"read error", r"write error", r"scsi", r"sda"],
        "NET": [r"connection down", r"eth", r"link down", r"setting node state to down"],
        "PRO": [r"cpu", r"processor", r"core failure", r"overheating"]
    }

    @classmethod
    def classify_category(cls, message: str) -> str:
        """
        Determine the error category of a message (default: ``OTH``).

        Args:
            message (str): raw message.

        Returns:
            str: first category whose pattern matches, or ``"OTH"``.
        """
        msg_lower = message.lower()
        for cat, patterns in cls.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    return cat
        return "OTH"

    @classmethod
    def filter_and_format(cls, raw_line: str, default_node: str = "tg-master") -> Optional[str]:
        """
        Keep only relevant errors, anonymise and format the line as:
        ``<timestamp_epoch> <node> <category> <message>``.

        Args:
            raw_line (str): raw log line.
            default_node (str): node name to write in the output.

        Returns:
            str | None: formatted line (with trailing newline), or None if the
            line is empty or is not an error message.
        """
        if not raw_line.strip():
            return None

        if not re.search(r"error|fatal|fail|critical|down", raw_line, re.IGNORECASE):
            return None  # Discard INFO/DEBUG messages

        timestamp = time.time()
        category = cls.classify_category(raw_line)

        # Basic anonymisation (masking of IPv4 addresses)
        clean_msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "X.X.X.X", raw_line.strip())

        return f"{timestamp:.0f} {default_node} {category} {clean_msg}\n"


# ==========================================
# 2. BASE MONITOR (Abstract)
# ==========================================

class BaseLogMonitor(abc.ABC):
    """
    Base class of the monitors: handles the output file and the running flag.

    Attributes:
        output_filepath (Path): file where formatted entries are appended.
        is_running (bool): capture loop flag.
    """

    def __init__(self, output_filepath: str):
        """
        Args:
            output_filepath (str): output log file.
        """
        self.output_filepath = Path(output_filepath)
        self.is_running = False

    def write_entry(self, formatted_entry: str):
        """Append the formatted line to the output file."""
        with open(self.output_filepath, "a", encoding="utf-8") as f:
            f.write(formatted_entry)
            f.flush()

    @abc.abstractmethod
    def start(self):
        """Start capturing."""
        pass

    def stop(self):
        """Stop capturing."""
        self.is_running = False
        print("Monitor fermato.")


# ==========================================
# 3. CONCRETE MONITORS
# ==========================================

class FileTailMonitor(BaseLogMonitor):
    """
    Follows a log file like ``tail -f`` and stores the error lines.

    Attributes:
        input_filepath (Path): file to follow.
        node_name (str): node name written in the output entries.
    """

    def __init__(self, input_filepath: str, output_filepath: str, node_name: str = "tg-c401"):
        """
        Args:
            input_filepath (str): file to follow.
            output_filepath (str): output log file.
            node_name (str): node name for the entries.
        """
        super().__init__(output_filepath)
        self.input_filepath = Path(input_filepath)
        self.node_name = node_name

    def start(self, poll_interval: float = 0.5):
        """
        Start following the file (blocking, until stop or Ctrl+C).

        Args:
            poll_interval (float): seconds to wait when no new line is available.
        """
        self.is_running = True
        print(f"[*] Avvio FileTailMonitor su: {self.input_filepath}")

        if not self.input_filepath.exists():
            self.input_filepath.touch()

        with open(self.input_filepath, "r", encoding="utf-8") as f:
            # Move to the end of the file: only new lines are processed
            f.seek(0, 2)

            try:
                while self.is_running:
                    line = f.readline()
                    if not line:
                        # No new data yet: wait and retry
                        time.sleep(poll_interval)
                        continue

                    formatted = LogFilterEngine.filter_and_format(line, default_node=self.node_name)
                    if formatted:
                        self.write_entry(formatted)
                        print(f"[LOG CATTURATO] {formatted.strip()}")

            except KeyboardInterrupt:
                self.stop()


class SyslogServerMonitor(BaseLogMonitor):
    """
    Minimal UDP syslog server that stores the error messages received.

    Attributes:
        host (str): listening address.
        port (int): listening UDP port.
    """

    def __init__(self, output_filepath: str, host: str = "0.0.0.0", port: int = 5140):
        """
        Args:
            output_filepath (str): output log file.
            host (str): listening address.
            port (int): UDP port.
        """
        super().__init__(output_filepath)
        self.host = host
        self.port = port  # 5140 to avoid root privileges (port 514 requires root)

    def start(self):
        """Receive datagrams and store the error messages (blocking, until Ctrl+C)."""
        self.is_running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"[*] Server Syslog attivo su UDP {self.host}:{self.port}")

        try:
            while self.is_running:
                data, addr = sock.recvfrom(4096)
                raw_message = data.decode("utf-8", errors="ignore")
                # Sender IP address used as node identifier
                node_ip = addr[0]

                formatted = LogFilterEngine.filter_and_format(raw_message, default_node=f"node-{node_ip}")
                if formatted:
                    self.write_entry(formatted)
                    print(f"[SYSLOG RECEIVED] {formatted.strip()}")

        except KeyboardInterrupt:
            self.stop()
        finally:
            sock.close()
