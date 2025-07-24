import csv

input_file = 'songdo_apartments_listings.csv'
temp_file = 'songdo_apartments_listings_temp.csv'

with open(input_file, 'r', encoding='utf-8') as infile, open(temp_file, 'w', encoding='utf-8', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    header = next(reader)
    writer.writerow(header)
    for row in reader:
        if len(row) >= 7:
            complex_name = row[0].strip()
            floor_info = row[6].strip()
            # Step 1: Move 29층 listings from A동 to 센텀하이브B동오피스
            if complex_name == '더샵송도센텀하이브A' and floor_info.endswith('/29'):
                row[0] = '센텀하이브B동오피스'
        # Step 2: For all 센텀하이브B동오피스, set dong to 'B동'
        if row[0].strip() == '센텀하이브B동오피스':
            row[-1] = 'B동'
            # Step 3: If 2nd floor, reclassify as 상가
            if floor_info.startswith('2/') or floor_info == '2':
                row[0] = '센텀하이브B동상가'
                row[-1] = 'B동'  # 상가도 B동으로 명확히
        writer.writerow(row)
import os
os.replace(temp_file, input_file) 