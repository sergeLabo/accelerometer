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
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
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
    k = 1.0
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


class OSC:
    """Ne fait que envoyer avec self.client
    et recevoir avec self.server, en com avec service.py
    """

    def __init__(self):
        self.sensor = "\nRecherche d'un capteur ..."
        # a, b, c, activity, num, tempo
        self.display_list = [0, 0, 0, -2, 0, 1, 0]
        self.histo = []
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

        # dans service: t=int(time()*1000)-1604000000000 get_datetime() convertit
        t_absolute = get_datetime(t)

        # Datetime du début
        if not self.t_init:
            self.t_init = t_absolute
        t_relativ = t_absolute - self.t_init
        # Dizième de secondes
        tx = t_relativ.total_seconds()*10

        norme = int((a**2 + b**2 + c**2)**0.5)
        # liste de couple (x, y)
        if norme > 10:
            # Norme
            self.histo.append((tx, norme))
            # Par axe
            self.histo_xyz.append((tx, (a, b, c)))
            if len(self.histo) > self.lenght:
                del self.histo[0]
                del self.histo_xyz[0]


class MainScreen(Screen):
    pass


class Screen2(Screen):
    """Affichage en courbe de la dernière minute des normes du vecteur
    Accélération, actualisée toutes les 2 secondes
    """

    # #graph_id = ObjectProperty()

    def __init__(self, **kwargs):
        """self.graph ne peut pas être initié ici.
        Il doit être dans une autre méthode et appelé plus tard.
        """

        super().__init__(**kwargs)
        self.app = App.get_running_app()

        self.graph = None
        self.ylabel = "Norme du vecteur accélération"
        self.titre = "Accelerometer"
        self.xlabel = "Dixième de Secondes"
        self.x_ticks_minor = 5
        self.x_ticks_major = 100
        self.y_ticks_major = 3000
        self.xmin = -500
        self.xmax = 0
        self.ymin = -10000
        self.ymax =  10000
        self.top = 0

        # Initialisation des courbes avec la couleur
        self.curve_norme = MeshLinePlot(color=[0, 0, 0, 1])
        self.curve_norme.points = []

        self.curve_x = MeshLinePlot(color=[0, 0.8, 0, 1])
        self.curve_x.points = []

        self.curve_y = MeshLinePlot(color=[0.8, 0, 0, 1])
        self.curve_y.points = []

        self.curve_z = MeshLinePlot(color=[0, 0, 0.8, 1])
        self.curve_z.points = []

        # Appel tous les 2 secondes
        Clock.schedule_once(self._once, 1)

    def _once(self, dt):
        Clock.schedule_interval(self.update, 0.1)
        self.create_graph()

    def update(self, dt):
        self.curve_norme.points = []
        self.curve_x.points = []
        self.curve_y.points = []
        self.curve_z.points = []

        if len(self.app.osc.histo) > 5:
            if self.top % 100 == 0:
                self.top += 1
                print("Optimisation de l'échelle des y")
                # #self.update_y_min_max()
            for couple in self.app.osc.histo:
                x = couple[0] - self.app.osc.histo[0][0] - 500
                y = couple[1]
                self.curve_norme.points.append((x, y))
            for couple in self.app.osc.histo_xyz:
                x = couple[0] - self.app.osc.histo[0][0] - 500
                y = couple[1][0]
                self.curve_x.points.append((x, y))
            for couple in self.app.osc.histo_xyz:
                x = couple[0] - self.app.osc.histo[0][0] - 500
                y = couple[1][1]
                self.curve_y.points.append((x, y))
            for couple in self.app.osc.histo_xyz:
                x = couple[0] - self.app.osc.histo[0][0] - 500
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

        # #self.graph.add_plot(self.curve_norme)
        self.graph.add_plot(self.curve_x)
        self.graph.add_plot(self.curve_y)
        self.graph.add_plot(self.curve_z)
        self.ids.graph_id.add_widget(self.graph)

    def update_y_min_max(self):
        a = (self.ymin, self.ymax)
        if len(self.app.osc.histo) > 5:
            ymin = 10000
            ymax = 1
            for couple in self.app.osc.histo:
                if couple[1] > ymax:
                    ymax = couple[1]
                if couple[1] < ymin:
                    ymin = couple[1]

        # Changement d'échelle y si beaaucoup d'écart
        if  ymin < 1.3*self.ymin or\
            ymin > 1.3*self.ymin or\
            ymax > 1.3*self.ymax or\
            ymax < 1.3*self.ymax:
            self.ymin = ymin
            self.ymax = ymax
            self.create_graph()


class Screen1(Screen):
    """Ecran d'affichage des datas envoyées par service.py
    et reçues dans self.app.osc
    """

    activity = NumericProperty(-1)

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
            self.ids.acceleromer_status.text = "Stop Accelerometer"
            self.freq = self.app.frequency  # vient de *.ini
            self.app.osc.client.send_message(b'/frequency', [self.freq])
            print("Envoi de /freq :", self.freq)

        elif self.sensor_status == 1:
            self.sensor_status = 0
            self.ids.acceleromer_status.text = "Start Accelerometer"

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
        print(activity)
        if activity == 0:
            activity_str = "Application réduite"
        elif activity == 1:
            activity_str = "Application plein ecran\nCouvercle rabattu"
        elif activity == 2:
            activity_str = "Application plein ecran\nCouvercle ouvert"
        elif activity == 3:
            activity_str = "Application plein ecran\nCouvercle rabattu\nen mouvement"
        else:
            activity_str = "\nVous devez sélectionner une activité !\n\n"

        self.ids.x_y_z.text = str(num) + "   ---      X: " + str(a) + "   Y: " + str(b) + "   Z: " + str(c)
        self.ids.activity_label.text = "Activité:\n" + activity_str
        self.ids.th_freq.text = f"Fréquence à obtenir = 10"
        self.ids.real_freq.text = f"Fréquence réelle = {real_freq}"
        self.ids.activ_sensor.text = f"Capteur actif: {self.app.osc.sensor}"

    def do_save_npz(self):
        self.app.osc.client.send_message(b'/save_npz', [1])
        self.ids.save_npz.text = "...."

    def reset_save_npz_button(self, dt):
        self.ids.save_npz.text = "Enregistrement"

    def do_quit(self):
        self.app.do_quit()


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
                            {'frequency': 50})

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
    """de int(time()*1000), retourne datetime"""
    return datetime.fromtimestamp((date + 1604000000000)/1000)

if __name__ == '__main__':
    AccelerometerApp().run()


"""dir self.curve_norme

'apply_property', 'ask_draw', 'bind', 'color', 'create_drawings', 'create_property', 'dispatch', 'dispatch_children', 'dispatch_generic', 'draw', 'events', 'fbind', 'funbind', 'funcx', 'funcy', 'get_drawings', 'get_group', 'get_property_observers', 'get_px_bounds', 'getter', 'is_event_type', 'iterate_points',
'mode',
'on_clear_plot', 'params', 'plot_mesh',
'points',
'properties', 'property', 'proxy_ref', 'register_event_type', 'set_mesh_size', 'setter', 'uid', 'unbind', 'unbind_uid', 'unproject', 'unregister_event_types', 'update', 'x_axis', 'x_px', 'y_axis', 'y_px'

"""
