import copy
import csv
import datetime as dt

import matplotlib.dates as mdates
import matplotlib.path
import matplotlib.pyplot as plt

import convert
from config_handler import ConfigHandler


# matplotlib 3.10.x has a broken Path.__deepcopy__ that calls
# copy.deepcopy(super(), memo), which recurses infinitely on Python 3.14.
# Replace it with a straightforward __dict__ copy.
def _path_deepcopy(self, memo):
    cls = self.__class__
    result = cls.__new__(cls)
    memo[id(self)] = result
    for k, v in self.__dict__.items():
        setattr(result, k, copy.deepcopy(v, memo))
    return result


matplotlib.path.Path.__deepcopy__ = _path_deepcopy


def show_full_graph():
    dates = []
    balances = []
    ch = ConfigHandler()

    with open(ch.get("betting_files", "balance_history"), "r") as csv_file:
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

    ax.set(title="Balance history")

    plt.gcf().autofmt_xdate()
    plt.legend()

    plt.savefig("balance_history.png")
    plt.show()
