import os
import csv
from typing import List, Dict, Any
import ast
import json

class AuditUtils:
    
    def write_json_list_to_csv(self, json_list: List[Dict[str, Any]], filename: str) -> None:
        """
        Writes a list of JSON objects to a CSV file.

        Parameters:
        ----------
        json_list : List[Dict[str, Any]]
            A list of dictionaries (JSON-like structures) to be written into the CSV file.
        filename : str
            The name of the CSV file to write the data into.

        Returns:
        -------
        None
        """
        self.default_save_folder = "audit_events_output"
        if not json_list:
            print("No data to write to CSV.")
            return

        # Ensure all items in json_list are dictionaries
        processed_rows = []
        for row in json_list:
            new_row = row.copy()
            data = row["data"]
            if isinstance(data, dict):
                try:
                    new_row["details_id"] = data.get("id")
                    new_row["details_status"] = data.get("status")
                    new_row["details_username"] = data.get("username")
                except Exception as e:
                    new_row["details_id"] = None
                    new_row["details_status"] = None
                    new_row["details_username"] = None
            new_row.pop("data")
            row.pop("data")
            processed_rows.append(new_row)
        base_keys = list(json_list[0].keys())
        breakout_keys = ["details_id", "details_status", "details_username"]
        fieldnames = base_keys + [k for k in breakout_keys if k not in base_keys]
        # Ensure the target folder exists
        if not os.path.exists(self.default_save_folder):
            os.makedirs(self.default_save_folder)

        csv_filename = os.path.join(self.default_save_folder, filename)

        # Write to CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            dict_writer.writeheader()
            dict_writer.writerows(processed_rows)

        print(f"Data successfully written to {csv_filename}")