"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-46m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import abc
import time
import re
import socket
from typing import Optional, Callable
from pathlib import Path

class LogFilterEngine:
    CATEGORY_PATTERNS = {
        "DEV": [r"pci", r"device", r"hardware failure", r"bus failure"],
        "MEM": [r"ecc", r"ram", r"memory", r"dimm"],
        "I-O": [r"disk", r"storage", r"read error", r"write error", r"scsi", r"sda"],
        "NET": [r"connection down", r"eth", r"link down", r"setting node state to down"],
        "PRO": [r"cpu", r"processor", r"core failure", r"overheating"]
    }

    @classmethod
    def classify_category(cls, message: str) -> str:
        """Determina la categoria dell'errore (default: OTH)[cite: 2]."""
        msg_lower = message.lower()
        for cat, patterns in cls.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    return cat
        return "OTH"  #[cite: 2]

    @classmethod
    def filter_and_format(cls, raw_line: str, default_node: str = "tg-master") -> Optional[str]:
        """
        Filtra solo gli errori rilevanti, anonimizza e formatta la riga come:
        <timestamp_epoch> <nodo> <categoria> <messaggio>
        """
        if not raw_line.strip():
            return None

        if not re.search(r"error|fatal|fail|critical|down", raw_line, re.IGNORECASE):
            return None  # Scarta messaggi di INFO/DEBUG

        timestamp = time.time()
        category = cls.classify_category(raw_line)
        
        # Anonimizzazione base (rimozione di IP o path utente)
        clean_msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "X.X.X.X", raw_line.strip())
        
        return f"{timestamp:.0f} {default_node} {category} {clean_msg}\n"


# ==========================================
# 2. BASE MONITOR (Abstract)
# ==========================================

class BaseLogMonitor(abc.ABC):
    def __init__(self, output_filepath: str):
        self.output_filepath = Path(output_filepath)
        self.is_running = False

    def write_entry(self, formatted_entry: str):
        """Scrive la riga formattata nel file di output."""
        with open(self.output_filepath, "a", encoding="utf-8") as f:
            f.write(formatted_entry)
            f.flush()

    @abc.abstractmethod
    def start(self):
        """Avvia la cattura."""
        pass

    def stop(self):
        """Interrompe la cattura."""
        self.is_running = False
        print("Monitor fermato.")


# ==========================================
# 3. CONCRETE MONITORS
# ==========================================

class FileTailMonitor(BaseLogMonitor):
    def __init__(self, input_filepath: str, output_filepath: str, node_name: str = "tg-c401"):
        super().__init__(output_filepath)
        self.input_filepath = Path(input_filepath)
        self.node_name = node_name

    def start(self, poll_interval: float = 0.5):
        self.is_running = True
        print(f"[*] Avvio FileTailMonitor su: {self.input_filepath}")

        if not self.input_filepath.exists():
            self.input_filepath.touch()

        with open(self.input_filepath, "r", encoding="utf-8") as f:
            f.seek(0, 2)

            try:
                while self.is_running:
                    line = f.readline()
                    if not line:
                        time.sleep(poll_interval)
                        continue

                    formatted = LogFilterEngine.filter_and_format(line, default_node=self.node_name)
                    if formatted:
                        self.write_entry(formatted)
                        print(f"[LOG CATTURATO] {formatted.strip()}")

            except KeyboardInterrupt:
                self.stop()


class SyslogServerMonitor(BaseLogMonitor):
    def __init__(self, output_filepath: str, host: str = "0.0.0.0", port: int = 5140):
        super().__init__(output_filepath)
        self.host = host
        self.port = port  # 5140 per evitare privilegi root (porta 514 richiede root)

    def start(self):
        self.is_running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"[*] Server Syslog attivo su UDP {self.host}:{self.port}")

        try:
            while self.is_running:
                data, addr = sock.recvfrom(4096)
                raw_message = data.decode("utf-8", errors="ignore")
                node_ip = addr[0]

                formatted = LogFilterEngine.filter_and_format(raw_message, default_node=f"node-{node_ip}")
                if formatted:
                    self.write_entry(formatted)
                    print(f"[SYSLOG RECEIVED] {formatted.strip()}")

        except KeyboardInterrupt:
            self.stop()
        finally:
            sock.close()