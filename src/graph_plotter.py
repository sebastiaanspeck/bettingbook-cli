import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplcursors
import csv

import convert

from config_handler import ConfigHandler


def show_full_graph():
    dates = []
    balances = []
    ch = ConfigHandler()

    with open(ch.get_data("betting_files")["balance_history"], "r") as csv_file:
        plots = csv.reader(csv_file, delimiter=",")
        for row in plots:
            dates.append(row[0])
            balances.append(float(row[1]))

    date_format = convert.format_date(ch.get("profile", "date_format"))
    dates = [dt.datetime.strptime(d, date_format) for d in dates]

    _, ax = plt.subplots()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())

    ax.plot(dates, balances, marker=".", color="red", label="Balance")

    mplcursors.cursor(hover=True)

    ax.set(title="Balance history")

    plt.gcf().autofmt_xdate()
    plt.legend()

    plt.savefig("balance_history.png")
