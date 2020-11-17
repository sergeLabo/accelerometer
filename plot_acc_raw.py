#!python3

import os, sys
from time import mktime
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
# #from numpy.linalg import norm  # all_norm = norm(, 2)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():

    kwargs = {  "PAQUET": 50,
                "gliss": 10
             }

    fd = FormattingData(**kwargs)


class FormattingData:

    def __init__(self, **kwargs):

        self.PAQUET = kwargs.get('PAQUET', None)
        self.gliss = kwargs.get('gliss', None)

        all_x, all_y, all_z, all_a, all_t, normes = self.get_datas()
        self.plot(all_x, all_y, all_z, all_a, all_t, normes)

    def get_datas(self):
        """Les datas sont regroupées par tuple de (norme, activité)"""

        all_x = all_y = all_z = all_a = None
        all_npz = Path("./npz").glob('**/*.npz')
        # Lecture dans l'ordre d'enregistrement
        for npz in sorted(all_npz):
            print(f"Fichier lu {npz}")
            data = np.load(npz)
            # #if all_x is not None:
                # #all_x = np.hstack((all_x, data["x"]))
                # #all_y = np.hstack((all_y, data["y"]))
                # #all_z = np.hstack((all_z, data["z"]))
                # #all_a = np.hstack((all_a, data["activity"]))
                # #all_t = np.hstack((all_t, data["t"]))
            # #else:
            all_x = data["x"]
            all_y = data["y"]
            all_z = data["z"]
            all_a = data["activity"]
            all_t = data["t"]
        print(f"Shape de toutes les datas: {all_x.shape}")

        normes = []
        for i in range(all_x.shape[0]):
            normes.append(int((all_x[i]**2 + all_y[i]**2 + all_z[i]**2 )**0.5))

        return  all_x, all_y, all_z, all_a, all_t, normes

    def plot(self, all_x, all_y, all_z, all_a, all_t, normes):
        x_values = []
        for i in range(len(all_t)):
            t_absolute = get_datetime(all_t[i])
            x_values.append(t_absolute)
        # t_absolute = 2020-11-11 16:49:19.495000

        debut = x_values[0].replace(microsecond=0).isoformat(' ')
        fin = x_values[-1].replace(microsecond=0).isoformat(' ')
        print("Heure de début =", debut)
        print("Heure de fin   =", fin)
        duree = x_values[0] - x_values[-1]
        print("Durée          =", duree)

        fig, ax1 = plt.subplots(1, 1, figsize=(20,10), facecolor='#cccccc')
        ax1.set_facecolor('#eafff5')
        l = 'Accélération de ' + str(debut) + ' à ' + str(fin)
        ax1.set_title(l, size=24, color='black')

        ax1.set_xlabel('Time')
        ax1.set_ylabel('Accélération', color='black')
        ax1.format_xdata = mdates.DateFormatter('%H-%M')

        a = ax1.scatter(x_values, normes,
                        marker = 'X',
                        linewidth=0.05,
                        color='black',
                        label="Accélération")
        a = ax1.scatter(x_values, all_x,
                        marker = 'X',
                        linewidth=0.05,
                        color='blue')
        a = ax1.scatter(x_values, all_y,
                        marker = 'X',
                        linewidth=0.05,
                        color='green')
        a = ax1.scatter(x_values, all_z,
                        marker = 'X',
                        linewidth=0.05,
                        color='red')

        ax1.tick_params(axis='y', labelcolor='black')

        # instantiate a second axes that shares the same x-axis
        ax2 = ax1.twinx()
        # we already handled the x-label with ax1
        ax2.set_ylabel('Activity', color='tab:red')
        ax2.tick_params(axis='y', labelcolor='black')

        b = ax2.plot(x_values, all_a,
                    linestyle="-",
                    linewidth=1.5,
                    color='orange',
                    label="Activity")

        # Définition de l'échelle des x
        mini = x_values[0]
        maxi = x_values[-1]
        ax1.set_xlim(mini, maxi)
        ax2.set_xlim(mini, maxi)

        print("Fréquence =", 6480/181)
        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        ax1.legend(loc="upper center")
        ax2.legend(loc="upper right")

        plt.show()


def get_datetime(date):
    """de int(time()*1000), retourne un datetime"""
    return datetime.fromtimestamp((date + 1604000000000)/1000)


if __name__ == "__main__":
    main()
