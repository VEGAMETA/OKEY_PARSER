import csv
import config


def save_to_csv(data_list: list[list]) -> None:
    """
    Saves data to csv file
    :param data_list: data
    :return:
    """
    try:
        with open(config.csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(data_list)
        print("Done!")
    except Exception as e:
        print(e)
