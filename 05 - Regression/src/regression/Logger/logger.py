"""
 * author Antonio Sirignano
 * created on 09-10-2026-15h-09m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd

class CSVLogger:
    def __init__(self, output_filename: str):
        self.output_filename = output_filename
        self._is_header_written = False

    def log_sample(self, sample_data: dict):
        df_row = pd.DataFrame([sample_data])
        df_row.to_csv(self.output_filename,
                      mode='a',
                      index=False,
                      header= not self._is_header_written,
                      )
        self._is_header_written = True

    