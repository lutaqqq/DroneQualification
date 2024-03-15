import tkinter as tki
from tkinter import Toplevel, Scale
import threading
import datetime
import os
import time
import platform
import cv2
from PIL import Image, ImageTk

class TelloUI(object):
    """
    Оболочка для включения графического интерфейса пользователя (GUI).
    """
    def __init__(self, tello):
        """
        Инициализирует все элементы GUI, поддерживаемые Tkinter.

        :param tello: класс взаимодействует с дроном Tello.
        """
        self.tello = tello  # устройство видеопотока
        self.thread = None  # поток Tkinter mainloop
        self.stopEvent = None

        # управляющие переменные
        self.distance = 0.1  # расстояние по умолчанию для команды 'move'
        self.degree = 30  # угол по умолчанию для команд 'cw' или 'ccw'

        # если флаг TRUE, поток автоматического взлета прекратит ожидание
        # ответа от дрона
        self.quit_waiting_flag = False

        # инициализировать основное окно и панель изображения
        self.root = tki.Tk()
        self.panel = None

        # создать кнопки
        self.btn_landing = tki.Button(
            self.root, text='Открыть панель команд', relief='raised', command=self.openCmdWindow)
        self.btn_landing.pack(side='bottom', fill='both',
                              expand='yes', padx=10, pady=5)
        self.btn_cam = tki.Button(
            self.root, text='Запустить камеру', relief='raised', command=self.activate_cam)
        self.btn_cam.pack(side='bottom', fill='both', expand='yes', padx=10, pady=5)

        # начать поток, который постоянно проверяет видеопоток
        self.stopEvent = threading.Event()

        # установить обратный вызов для обработки закрытия окна
        self.root.wm_title('Контроллер TELLO')
        self.root.wm_protocol('WM_DELETE_WINDOW', self.on_close)

        # поток отправки команд будет отправлять команду к дрону каждые 5 секунд
        self.sending_command_thread = threading.Thread(target=self._sendingCommand)

    def _sendingCommand(self):
        """
        Запускает цикл while, который отправляет 'command' к дрону каждые 5 секунд.

        :return: None
        """

        while True:
            self.tello.send_command('command')
            time.sleep(5)

    def _setQuitWaitingFlag(self):
        """
        Устанавливает переменную как TRUE; это прекратит ожидание ответа от дрона компьютером.

        :return: None
        """
        self.quit_waiting_flag = True

    def openCmdWindow(self):
        """
        Открывает окно команд и инициализирует все кнопки и текст.

        :return: None
        """
        panel = Toplevel(self.root)
        panel.wm_title('Панель команд')

        # создать текстовый ввод
        text0 = tki.Label(panel,
                          text='Команды клавиатурного управления Tello\n'
                               'Отрегулируйте бегунок, чтобы настроить параметры высоты и угла',
                          font='Helvetica 10 bold'
                          )
        text0.pack(side='top')

        text1 = tki.Label(panel, text=
                          'W - Подняться\t\t\t\tСтрелка Вверх - Движение вперед\n'
                          'S - Спуститься\t\t\t\tСтрелка Вниз - Движение назад\n'
                          'A - Поворот против часовой стрелки\tСтрелка Влево - Движение влево\n'
                          'D - Поворот по часовой стрелке\t\tСтрелка Вправо - Движение вправо',
                          justify='left')
        text1.pack(side='top')

        self.btn_landing = tki.Button(
            panel, text='Посадка', relief='raised', command=self.telloLanding)
        self.btn_landing.pack(side='bottom', fill='both',
                              expand='yes', padx=10, pady=5)

        self.btn_takeoff = tki.Button(
            panel, text='Взлет', relief='raised', command=self.telloTakeOff)
        self.btn_takeoff.pack(side='bottom', fill='both',
                              expand='yes', padx=10, pady=5)

        # привязка клавиш стрелок к управлению дроном
        self.tmp_f = tki.Frame(panel, width=100, height=2)
        self.tmp_f.bind('<KeyPress-w>', self.on_keypress_w)
        self.tmp_f.bind('<KeyPress-s>', self.on_keypress_s)
        self.tmp_f.bind('<KeyPress-a>', self.on_keypress_a)
        self.tmp_f.bind('<KeyPress-d>', self.on_keypress_d)
        self.tmp_f.bind('<KeyPress-Up>', self.on_keypress_up)
        self.tmp_f.bind('<KeyPress-Down>', self.on_keypress_down)
        self.tmp_f.bind('<KeyPress-Left>', self.on_keypress_left)
        self.tmp_f.bind('<KeyPress-Right>', self.on_keypress_right)
        self.tmp_f.pack(side='bottom')
        self.tmp_f.focus_set()

        self.btn_landing = tki.Button(
            panel, text='Флип', relief='raised', command=self.openFlipWindow)
        self.btn_landing.pack(side='bottom', fill='both',
                              expand='yes', padx=10, pady=5)

        self.distance_bar = Scale(panel, from_=0.02, to=5, tickinterval=0.01,
                                  digits=3, label='Высота (м)',
                                  resolution=0.01)
        self.distance_bar.set(0.2)
        self.distance_bar.pack(side='left')

        self.btn_distance = tki.Button(panel, text='Сбросить высоту', relief='raised',
                                       command=self.updateDistancebar,
                                       )
        self.btn_distance.pack(side='left', fill='both',
                               expand='yes', padx=10, pady=5)

        self.degree_bar = Scale(panel, from_=1, to=360, tickinterval=10, label='Угол')
        self.degree_bar.set(30)
        self.degree_bar.pack(side='right')

        self.btn_distance = tki.Button(panel, text='Сбросить угол', relief='raised',
                                       command=self.updateDegreebar)
        self.btn_distance.pack(side='right', fill='both',
                               expand='yes', padx=10, pady=5)

    def activate_cam(self):
        # Создаем окно для отображения камеры
        self.cam_window = Toplevel(self.root)
        self.cam_window.wm_title('Прямой поток изображения с камеры')

        # Открываем камеру с помощью OpenCV
        cap = cv2.VideoCapture(0)  # Номер камеры может отличаться в зависимости от вашей конфигурации

        # Чтение изображения из камеры и отображение его в окне Tkinter
        while True:
            ret, frame = cap.read()  # Чтение кадра из камеры

            if ret:  # Если успешно получено изображение
                # Преобразование кадра в формат ImageTk
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                image = ImageTk.PhotoImage(image)

                # Обновление изображения в окне Tkinter
                label = tki.Label(self.cam_window, image=image)
                label.image = image  # Сохраняем ссылку на изображение
                label.pack()

            # Прерывание цикла при закрытии окна
            if cv2.getWindowProperty('Прямой поток изображения с камеры', cv2.WND_PROP_VISIBLE) < 1:
                break

            # Обновляем окно Tkinter
            self.root.update()

        # Освобождение ресурсов
        cap.release()
        cv2.destroyAllWindows()

    def openFlipWindow(self):
        """
        Открывает окно флипа и инициализирует все кнопки и текст.

        :return: None
        """
        panel = Toplevel(self.root)
        panel.wm_title('Распознавание жестов')

        self.btn_flipl = tki.Button(
            panel, text='Флип влево', relief='raised', command=self.telloFlip_l)
        self.btn_flipl.pack(side='bottom', fill='both',
                            expand='yes', padx=10, pady=5)

        self.btn_flipr = tki.Button(
            panel, text='Флип вправо', relief='raised', command=self.telloFlip_r)
        self.btn_flipr.pack(side='bottom', fill='both',
                            expand='yes', padx=10, pady=5)

        self.btn_flipf = tki.Button(
            panel, text='Флип вперед', relief='raised', command=self.telloFlip_f)
        self.btn_flipf.pack(side='bottom', fill='both',
                            expand='yes', padx=10, pady=5)

        self.btn_flipb = tki.Button(
            panel, text='Флип назад', relief='raised', command=self.telloFlip_b)
        self.btn_flipb.pack(side='bottom', fill='both',
                            expand='yes', padx=10, pady=5)

    def telloTakeOff(self):
        return self.tello.takeoff()

    def telloLanding(self):
        return self.tello.land()

    def telloFlip_l(self):
        return self.tello.flip('l')

    def telloFlip_r(self):
        return self.tello.flip('r')

    def telloFlip_f(self):
        return self.tello.flip('f')

    def telloFlip_b(self):
        return self.tello.flip('b')

    def telloCW(self, degree):
        return self.tello.rotate_cw(degree)

    def telloCCW(self, degree):
        return self.tello.rotate_ccw(degree)

    def telloMoveForward(self, distance):
        return self.tello.move_forward(distance)

    def telloMoveBackward(self, distance):
        return self.tello.move_backward(distance)

    def telloMoveLeft(self, distance):
        return self.tello.move_left(distance)

    def telloMoveRight(self, distance):
        return self.tello.move_right(distance)

    def telloUp(self, dist):
        return self.tello.move_up(dist)

    def telloDown(self, dist):
        return self.tello.move_down(dist)

    def updateDistancebar(self):
        self.distance = self.distance_bar.get()
        print(f'сбросить расстояние до {self.distance:.1f}')

    def updateDegreebar(self):
        self.degree = self.degree_bar.get()
        print(f'сбросить угол до {self.degree}')

    def on_keypress_w(self, event):
        print(f'подняться на {self.distance} м')
        self.telloUp(self.distance)

    def on_keypress_s(self, event):
        print(f'опуститься на {self.distance} м')
        self.telloDown(self.distance)

    def on_keypress_a(self, event):
        print(f'по часовой стрелке на {self.degree} градусов')
        self.tello.rotate_ccw(self.degree)

    def on_keypress_d(self, event):
        print(f'против часовой стрелки на {self.degree} градусов')
        self.tello.rotate_cw(self.degree)

    def on_keypress_up(self, event):
        print(f'вперед на {self.distance} м')
        self.telloMoveForward(self.distance)

    def on_keypress_down(self, event):
        print(f'назад на {self.distance} м')
        self.telloMoveBackward(self.distance)

    def on_keypress_left(self, event):
        print(f'влево на {self.distance} м')
        self.telloMoveLeft(self.distance)

    def on_keypress_right(self, event):
        print(f'вправо на {self.distance} м')
        self.telloMoveRight(self.distance)

    def on_close(self):
        """
        Устанавливает событие остановки, очищает камеру и позволяет остальному
        процессу завершиться.
        :return: None
        """
        print('[INFO] закрытие...')
        self.stopEvent.set()
        del self.tello
        self.root.quit()
