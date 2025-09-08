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
            
            # A동 처리 (더샵송도센텀하이브A → 센텀하이브A동)
            if complex_name == '더샵송도센텀하이브A':
                try:
                    floor_num = int(floor_info.split('/')[0])
                    total_floors = int(floor_info.split('/')[1])
                    
                    if total_floors == 39:  # A동은 39층까지
                        if floor_num <= 2:
                            # 1-2층: 상가
                            row[0] = '센텀하이브A동상가'
                            row[-1] = 'A동'
                        elif floor_num >= 4:
                            # 4-39층: 오피스
                            row[0] = '센텀하이브A동오피스'
                            row[-1] = 'A동'
                except (ValueError, IndexError):
                    pass
            
            # B동 처리 (더샵송도센텀하이브B → 센텀하이브B동)
            elif complex_name == '더샵송도센텀하이브B':
                try:
                    floor_num = int(floor_info.split('/')[0])
                    total_floors = int(floor_info.split('/')[1])
                    
                    if total_floors == 29:  # B동은 29층까지
                        if floor_num <= 2:
                            # 1-2층: 상가
                            row[0] = '센텀하이브B동상가'
                            row[-1] = 'B동'
                        elif 3 <= floor_num <= 8:
                            # 3-8층: 오피스
                            row[0] = '센텀하이브B동오피스'
                            row[-1] = 'B동'
                        elif floor_num >= 10:
                            # 10-29층: 오피스텔
                            row[0] = '센텀하이브B동오피스텔'
                            row[-1] = 'B동'
                except (ValueError, IndexError):
                    pass
            
            # 이미 분류된 센텀하이브 매물들 처리
            elif complex_name in ['센텀하이브A동상가', '센텀하이브A동오피스', 
                                 '센텀하이브B동상가', '센텀하이브B동오피스텔']:
                # 이미 올바르게 분류된 매물들은 그대로 유지
                pass
        
        writer.writerow(row)

import os
os.replace(temp_file, input_file)
print("센텀하이브 매물 분류가 완료되었습니다.") 