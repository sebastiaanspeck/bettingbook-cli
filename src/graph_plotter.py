import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplcursors
import csv

import convert

from config_handler import ConfigHandler


def show_full_graph():
    dates = []
    start = []
    end = []
    ch = ConfigHandler()

    with open(ch.get_data('betting_files')['balance_history'], 'r') as csv_file:
        plots = csv.reader(csv_file, delimiter=',')
        for row in plots:
            dates.append(row[0])
            start.append(float(row[1]))
            end.append(float(row[2]))

    date_format = convert.format_date(ch.get('profile', 'date_format'))
    dates = [dt.datetime.strptime(d, date_format) for d in dates]

    fig, ax = plt.subplots()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())

    ax.plot(dates, start, marker=".", color='red', label='Start balance')
    ax.plot(dates, end, marker=".", color='green', label='End balance')

    mplcursors.cursor()

    ax.set(xlabel='Date', ylabel='Balance', title='Balance history')
    fig.canvas.set_window_title('Balance history graph')

    plt.gcf().autofmt_xdate()
    plt.legend()

    plt.show()
