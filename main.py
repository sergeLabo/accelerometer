#!python3
# -*- coding: UTF-8 -*-

"""
Bug avec debian 10
    xclip and xsel - FileNotFoundError: [Errno 2]
résolu avec
    sudo apt install xclip

Compilation possible avec java 8 et non avec 11
sudo update-alternatives --config java
java -version
export JAVA_HOME=/usr/lib/jvm/adoptopenjdk-8-hotspot-amd64

Le service s'appelle Pong

Ne pas oublier d'autoriser les droits d'écriture dans Paramètres/Applications
sur Android.
"""


import os
from time import sleep
from datetime import datetime, timedelta
from runpy import run_path
from threading import Thread

import kivy
kivy.require('1.11.1')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy_garden.graph import Graph, MeshLinePlot


from plyer import utils

from oscpy.client import OSCClient
from oscpy.server import OSCThreadServer

print("Platform =", utils.platform)
ANDROID = utils.platform._platform_android  # retourne True ou False
print("Android =", ANDROID)
if not ANDROID:
    from kivy.core.window import Window
    # Simulation de l'écran de mon tél: 1280*720
    k = 0.8
    WS = (int(720*k), int(1280*k))
    Window.size = WS
    os.environ['JAVA_HOME'] = '/usr/lib/jvm/adoptopenjdk-8-hotspot-amd64'

from jnius import autoclass

"""
SERVICE_NAME = u'{packagename}.Service{servicename}'.format(
    packagename=u'org.kivy.accelerometer',
    servicename=u'ServicePong')

Structure = package.domain.package.name.ServiceToto
avec de buildozer.spec
package.domain = org.kivy
package.name = accelerometer
soit
org.kivy.accelerometer.ServicePong
"""

SERVICE_NAME = 'org.kivy.accelerometer.ServicePong'
print("SERVICE_NAME:", SERVICE_NAME)

TABLE = {   0: "Assis",
            1: "Debout",
            2: "Marche",
            3: "Escalier",
            4: "Assis ordinateur",
            5: "Debout téléphone",
            6: "Course",
            7: "Restaurant"}

TABLE_LONG = {  0: "Assis",
                1: "Debout sans marcher",
                2: "Marche",
                3: "Escalier:\nmontée ou descente",
                4: "Assis en travaillant\nsur un ordinateur",
                5: "Debout en téléphonant",
                6: "Course",
                7: "Assis à la table\nd'un restaurant"}


class OSC:
    """Ne fait que envoyer avec self.client
    et recevoir avec self.server, en com avec service.py
    """

    def __init__(self):
        self.sensor = "\nRecherche d'un capteur ..."
        # a, b, c, activity, num, tempo
        self.display_list = [0, 0, 0, 0, 0, 1, 0]
        self.histo_xyz = []
        self.server = OSCThreadServer()
        self.server.listen(address=b'localhost',port=3003, default=True)
        self.server.bind(b'/acc', self.on_acc)
        self.server.bind(b'/sensor', self.on_sensor)
        self.client = OSCClient(b'localhost', 3001)
        self.lenght = 500
        self.t_init = None

    def on_sensor(self, sens):
        """Valeur possible: Android Virtual No sensor"""
        self.sensor = sens.decode('utf-8')

    def on_acc(self, *args):
        # Nessressaire pour maj affichage si acc ne tourne pas
        self.display_list = [args[0], args[1], args[2], args[3],
                            args[4], args[5], args[6]]
        a, b, c, t = (args[0], args[1], args[2], args[6])

        # dans service: t=int(time()*1000)-1604000000000 avec get_datetime()
        t_absolute = get_datetime(t)

        # Datetime du début
        if not self.t_init:
            self.t_init = t_absolute
        t_relativ = t_absolute - self.t_init
        # Dizième de secondes
        tx = t_relativ.total_seconds()*10

        norme = int((a**2 + b**2 + c**2)**0.5)
        # #self.histo.append((tx, norme))
        # Par axe
        if norme > 1:  # Bug au début
            self.histo_xyz.append((tx, (a, b, c)))


class MainScreen(Screen):
    """Necéssaire pour la création de l'objet MainScreen"""
    pass


class Screen1(Screen):
    """Ecran d'affichage des datas envoyées par service.py
    et reçues dans self.app.osc
    """

    # #activity = NumericProperty(-1)
    # #action = ListProperty([0,1,2,3,4,5,6,7])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

        self.sensor_status = 0
        # Delay de boucle
        Clock.schedule_once(self.client_once, 1)

    def client_once(self, dt):
        Clock.schedule_interval(self.update_display, 1)

    def on_sensor_enable(self):
        """Envoi au service de l'info sensor enable or not"""

        if self.sensor_status == 0:
            self.sensor_status = 1
            self.ids.acceleromer_status.text = "Stopper l'accélèromètre"
            self.freq = self.app.frequency  # vient de *.ini
            self.app.osc.client.send_message(b'/frequency', [self.freq])
            print("Envoi de /freq :", self.freq)

        elif self.sensor_status == 1:
            self.sensor_status = 0
            self.ids.acceleromer_status.text = "Lancer l'accéléromètre"

        print("Envoi de sensor_status:", self.sensor_status)
        self.app.osc.client.send_message(b'/sensor_enable', [self.sensor_status])

    def on_activity(self, act):
        print("act", act)
        self.app.osc.client.send_message(b'/activity', [act])

    def update_display(self, dt):

        a, b, c, activity, num, real_freq, t = (self.app.osc.display_list[0],
                                                self.app.osc.display_list[1],
                                                self.app.osc.display_list[2],
                                                self.app.osc.display_list[3],
                                                self.app.osc.display_list[4],
                                                self.app.osc.display_list[5],
                                                self.app.osc.display_list[6])

        self.ids.x_y_z.text = str(num) + "\nX: " + str(a) + "  Y: " + str(b) + "  Z: " + str(c)
        self.ids.activity_long.text = "Activité:\n" + TABLE_LONG[activity]
        self.ids.real_freq.text = f"Fréquence  = {int(real_freq)}"
        self.ids.activ_sensor.text = f"Capteur actif: {self.app.osc.sensor}"

        for a in range(8):
            self.ids['action_' + str(a)].text = TABLE[a]

    def do_save_npz(self):
        self.app.osc.client.send_message(b'/save_npz', [1])
        self.ids.save_npz.text = "...."

    def reset_save_npz_button(self, dt):
        self.ids.save_npz.text = "Enregistrement"

    def do_quit(self):
        self.app.do_quit()


class Screen2(Screen):
    """Affichage en courbe de la dernière minute des normes du vecteur
    Accélération, actualisée toutes les 2 secondes
    """

    def __init__(self, **kwargs):
        """self.graph ne peut pas être initié ici.
        Il doit être dans une autre méthode et appelé plus tard.
        """

        super().__init__(**kwargs)
        self.app = App.get_running_app()

        self.graph = None
        self.ylabel = "Valeur des accélérations sur x y z"
        self.titre = "Accelerometer"
        self.xlabel = "Dixième de Secondes"
        self.x_ticks_minor = 5
        self.x_ticks_major = 100
        self.y_ticks_major = 3000
        self.xmin = -500
        self.xmax = 0
        self.ymin = -10000
        self.ymax =  10000
        self.gap = 0
        self.lenght = 0
        self.bf = 0

        # Initialisation des courbes avec la couleur
        self.curve_norme = MeshLinePlot(color=[0, 0, 0, 1])
        self.curve_norme.points = []

        self.curve_x = MeshLinePlot(color=[0, 0.8, 0, 1])
        self.curve_x.points = []

        self.curve_y = MeshLinePlot(color=[0.8, 0, 0, 1])
        self.curve_y.points = []

        self.curve_z = MeshLinePlot(color=[0, 0, 0.8, 1])
        self.curve_z.points = []

        Clock.schedule_once(self._once, 1)

    def _once(self, dt):
        Clock.schedule_interval(self.update, 0.1)
        self.create_graph()
        self.lenght = self.app.osc.lenght

    def histo_correction(self):
        """Les valeurs de temps manquantes sont mal affichée par Graph,
        il y a un saut du graphique au défilement, donc on ne voit pas le "trou"
        Correction de histo pour ajouter ces valeurs manquantes
        avec des valeurs xyz = 000
        hist = self.app.osc.histo_xy
        Entre 2 valeurs de histo: hist[i+1][0] - hist[i][0] = ~ 1.0
        Bizarre: ce devrait être 0.1 secondes
        """
        # TODO: Pourquoi 1 seconde
        hist = self.app.osc.histo_xyz
        if len(hist) > 2:
            for i in range(len(hist)):
                trou = hist[i][0] - hist[i-1][0]
                if trou > 2:
                    index = i  # 21
                    manque = int(trou - 1)
                    # Ajout des valeurs manquantes
                    debut = hist[index-1][0] + 1
                    for p in range(manque):
                        hist.insert(index + p, (debut + p*1.01, [0,0,0]))

        self.app.osc.histo_xyz = hist

    def update(self, dt):
        self.histo_correction()
        self.curve_norme.points = []
        self.curve_x.points = []
        self.curve_y.points = []
        self.curve_z.points = []

        if len(self.app.osc.histo_xyz) > 5:
            nb = len(self.app.osc.histo_xyz)
            if nb > self.lenght:
                d = nb + self.gap - self.lenght
                f = nb + self.gap
                if f == 0: f = nb
                t_debut = self.app.osc.histo_xyz[d][0]
                # il faut [-500:500] puis [-501:-1] puis [-502:-2]
                # -500 553 4.96 500
                for couple in self.app.osc.histo_xyz[d:f]:
                    self.add_couple(couple, t_debut)
            else:
                t_debut = self.app.osc.histo_xyz[0][0]
                for couple in self.app.osc.histo_xyz:
                    self.add_couple(couple, t_debut)

    def add_couple(self, couple, t_debut):
        x = couple[0] - t_debut - self.lenght
        y = couple[1][0]
        self.curve_x.points.append((x, y))
        y = couple[1][1]
        self.curve_y.points.append((x, y))
        y = couple[1][2]
        self.curve_z.points.append((x, y))

    def create_graph(self):
        print("Création du graph")
        if self.graph:
            self.ids.graph_id.remove_widget(self.graph)

        self.graph = Graph( background_color=(0.8, 0.8, 0.8, 1),
                            border_color=(0, 0.1, 0.1, 1),
                            xlabel=self.xlabel,
                            ylabel=self.ylabel,
                            x_ticks_minor=self.x_ticks_minor,
                            x_ticks_major=self.x_ticks_major,
                            y_ticks_major=self.y_ticks_major,
                            x_grid_label=True,
                            y_grid_label=True,
                            padding=10,
                            x_grid=True,
                            y_grid=True,
                            xmin=self.xmin,
                            xmax=self.xmax,
                            ymin=self.ymin,
                            ymax=self.ymax,
                            tick_color=(1, 0, 1, 1),
                            label_options={'color': (0.2, 0.2, 0.2, 1)})

        self.graph.add_plot(self.curve_x)
        self.graph.add_plot(self.curve_y)
        self.graph.add_plot(self.curve_z)
        self.ids.graph_id.add_widget(self.graph)

    def do_back_forward(self, sens):
        self.bf = 1
        bt = Thread(target=self.back_forward_loop, args=(sens, ), daemon=True)
        bt.start()

    def back_forward_loop(self, sens):
        while self.bf:
            sleep(0.1)
            self.gap = self.gap + sens*50
            if self.gap > 0: self.gap = 0
            l = len(self.app.osc.histo_xyz)
            if self.gap < -l + 500: self.gap = -l + 500
            print("Gap:", self.gap)

    def do_end(self):
        self.bf = 0

    def do_last(self):
        self.gap = 0
        print("Gap:", self.gap)


class Accelerometer(BoxLayout):

    def __init__(self, app, **kwargs):

        super().__init__(**kwargs)
        self.app = app

        self.service = None
        self.app.osc = OSC()
        self.start_service()

    def start_service(self):
        if ANDROID:
            # SERVICE_NAME = 'org.kivy.accelerometer.ServicePong'
            self.service = autoclass(SERVICE_NAME)
            self.m_activity = autoclass(u'org.kivy.android.PythonActivity').mActivity
            argument = 'android:hardwareAccelerated="true"'
            self.service.start(self.m_activity, argument)
        else:
            # Equivaut à:
            # run_path('./service.py', {'run_name': '__main__'}, daemon=True)
            self.service = Thread(  target=run_path,
                                    args=('service.py',),
                                    kwargs={'run_name': '__main__'},
                                    daemon=True)
            self.service.start()
            print("Thread lancé.")


class AccelerometerApp(App):

    def build(self):
        return Accelerometer(self)

    def on_start(self):
        self.frequency = int(self.config.get('accelerometer', 'frequency'))

    def build_config(self, config):
        config.setdefaults('accelerometer',
                            {'frequency': 10})

        config.setdefaults('kivy',
                            { 'log_level': 'debug',
                              'log_name': 'accelerometer_%y-%m-%d_%_.txt',
                              'log_dir': '/sdcard',
                              'log_enable': '1'})

        config.setdefaults('postproc',
                            { 'double_tap_time': 250,
                              'double_tap_distance': 20})

    def build_settings(self, settings):
        data = """[
                    {"type": "title", "title":"Configuration de l'accéléromètre"},
                    {"type": "numeric",
                      "title": "Fréquence",
                      "desc": "de 1 à 100",
                      "section": "accelerometer", "key": "frequency"}
                   ]"""

        # self.config est le config de build_config
        settings.add_json_panel('Accelerometer', self.config, data=data)

    def on_config_change(self, config, section, key, value):
        if config is self.config:  # du joli python rigoureux
            token = (section, key)

            # Frequency
            if token == ('accelerometer', 'frequency'):
                value = int(value)
                print("Nouvelle Fréquence:", value)
                if value < 1: value = 1
                if value >= 100: value = 100
                self.frequency = value
                self.osc.client.send_message(b'/frequency', [value])
                # Save in ini
                self.config.set('accelerometer', 'frequency', value)

    def on_pause(self):
        # Pour que l'application passe en pause si réduite, et continue si réactivée
        print("on_pause return True")
        return True

    def on_resume(self):
        # Pour que l'application passe en pause si fermée, et continue si réactivée
        print("on_resume return True")
        return True

    def do_quit(self):
        if ANDROID:
            self.service.stop(self.m_activity)
            self.service = None
        else:
            self.osc.client.send_message(b'/stop', [1])
            sleep(1)

        AccelerometerApp.get_running_app().stop()


def get_datetime(date):
    """de int(time()*1000), retourne datetime
    dans service.py
    1604000000000 pour être inférieur au  maxi de l'OSC
    tp = int(time()*1000) - 1604000000000
    """
    return datetime.fromtimestamp((date + 1604000000000)/1000)


if __name__ == '__main__':
    AccelerometerApp().run()
