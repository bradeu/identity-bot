import csv
import io
from typing import List, Dict, Any

logger_name = "csv_processor"

REQUIRED_COLUMNS = {
    'outcome', 'group_variable', 'group_label', 'n', 'n_flag',
    'pct_lib', 'pct_con', 'pct_ndp', 'pct_bq', 'pct_grn',
    'pct_other', 'pct_none', 'none_label', 'year', 'dataset', 'mode'
}


def _to_float(val: str):
    val = val.strip()
    return float(val) if val else None


def _to_int(val: str):
    val = val.strip()
    return int(val) if val else None


class CSVProcessor:
    def parse(self, csv_content: bytes) -> List[Dict[str, Any]]:
        text = csv_content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))

        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        rows = []
        for row in reader:
            rows.append({
                'outcome': row['outcome'],
                'group_variable': row['group_variable'],
                'group_label': row['group_label'],
                'n': _to_int(row['n']),
                'n_flag': row['n_flag'] or None,
                'pct_lib': _to_float(row['pct_lib']),
                'pct_con': _to_float(row['pct_con']),
                'pct_ndp': _to_float(row['pct_ndp']),
                'pct_bq': _to_float(row['pct_bq']),
                'pct_grn': _to_float(row['pct_grn']),
                'pct_other': _to_float(row['pct_other']),
                'pct_none': _to_float(row['pct_none']),
                'none_label': row['none_label'] or None,
                'year': _to_int(row['year']),
                'dataset': row['dataset'] or None,
                'mode': row['mode'] or None,
            })

        return rows
