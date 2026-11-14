"""
 * author Antonio Sirignano
 * created on 09-10-2026-15h-09m
 * github: https://github.com/antsiri
 * copyright 2026

Append-only CSV logger for monitoring samples.
"""

import pandas as pd


class CSVLogger:
    """
    Appends one sample (dict) per call to a CSV file, writing the header
    only on the first call.

    Attributes:
        output_filename (str): destination CSV.
    """

    def __init__(self, output_filename: str):
        """
        Args:
            output_filename (str): destination CSV.
        """
        self.output_filename = output_filename
        self._is_header_written = False

    def log_sample(self, sample_data: dict):
        """
        Append a sample to the CSV.

        Args:
            sample_data (dict): column name -> value.
        """
        df_row = pd.DataFrame([sample_data])
        # mode='a' appends; the header is written only the first time
        df_row.to_csv(self.output_filename,
                      mode='a',
                      index=False,
                      header= not self._is_header_written,
                      )
        self._is_header_written = True


