import csv
import codecs
from fastapi import UploadFile

def get_valid_columns() -> list[str]:
    valid_columns = [
        'ticket_id', 'type', 'organization', 'comment', 'coords', 'photo', 'photo_after', 'address', 'subdistrict', 'district', 'province', 'timestamp', 'state', 'star', 'count_reopen', 'last_activity'
    ]
    return valid_columns

def is_column_valid(column: str) -> bool:
    return column in get_valid_columns()

def validate_csv(file: UploadFile) -> tuple[bool, str]:
    try:
        if file.filename.endswith('.csv'):
            chunksize = 1
            csvReader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8-sig'))
            if all([is_column_valid(f) for f in csvReader.fieldnames]):
                return True, "Valid file type"
            
            raise ValueError(f"Invalid file column, Required: [{', '.join(get_valid_columns())}] but got [{', '.join(csvReader.fieldnames)}]")
        else:
            raise TypeError(f"Invalid file type, only accept .csv file, but got {file.filename}")
    except Exception as e:
        return False, str(e)