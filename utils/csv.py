import csv
import config


def save_to_csv(data_list) -> None:
    with open(config.csv_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(data_list)
