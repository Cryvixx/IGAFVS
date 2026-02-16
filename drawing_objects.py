# Тащим нужные штуки из PyQt5
# Qt - куча констант для цветов и стилей
# QPointF - класс для точек (координаты могут быть дробными)
from PyQt5.QtCore import Qt, QPointF
# QPen - для рисования линий (цвет и толщина)
# QBrush - для закрашивания фигур
from PyQt5.QtGui import QPen, QBrush

# Класс DrawingObjects - тут методы для рисования всякого
class DrawingObjects: 
    # @staticmethod значит, что метод статический (не нужен экземпляр класса чтобы его вызвать)
    @staticmethod
    def draw_point(painter, x, y):
        # painter - это типа "кисть" чтобы рисовать на экране
        # x, y - координаты где рисовать точку
        
        # Ставим перо (линию) чёрного цвета толщиной 2 пикселя
        painter.setPen(QPen(Qt.black, 2))
        # Ставим кисть (заливку) чёрного цвета
        painter.setBrush(QBrush(Qt.black))
        # Рисуем кружок в точке (x, y) радиусом 4 пикселя
        # QPointF(x, y) - просто точка с координатами x и y
        painter.drawEllipse(QPointF(x, y), 4, 4)

    @staticmethod
    def draw_line(painter, x1, y1, x2, y2):
        # Рисуем линию между двумя точками
        # (x1, y1) - первая точка, (x2, y2) - вторая
        
        # Чёрная линия толщиной 2 пикселя
        painter.setPen(QPen(Qt.black, 2))
        # int() превращает дробные числа в целые (экран работает с целыми пикселями)
        # Рисуем линию от (x1, y1) к (x2, y2)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    @staticmethod
    def draw_circle(painter, center_x, center_y, radius):
        # Рисуем окружность
        # center_x, center_y - координаты центра
        # radius - радиус
        
        # Чёрное перо толщиной 2 пикселя
        painter.setPen(QPen(Qt.black, 2))
        # drawEllipse рисует эллипс (или круг если ширина = высоте)
        # Параметры: левый край, верхний край, ширина, высота прямоугольника вокруг круга
        painter.drawEllipse(
            int(center_x - radius),      # Левый край (центр минус радиус)
            int(center_y - radius),      # Верхний край (центр минус радиус)
            int(radius * 2),             # Ширина (радиус * 2 = диаметр)
            int(radius * 2)              # Высота (радиус * 2 = диаметр)
        )

    @staticmethod
    def draw_polygon(painter, points):
        # Рисуем многоугольник (фигуру с несколькими углами)
        # points - список координат вершин [(x1,y1), (x2,y2), (x3,y3), ...]
        
        # Чёрное перо толщиной 2 пикселя
        painter.setPen(QPen(Qt.black, 2))
        # Проходим по всем вершинам многоугольника
        for i in range(len(points)):
            # Берём текущую точку
            x1, y1 = points[i]
            # Берём следующую точку (% len(points) - если это последняя, берём первую)
            x2, y2 = points[(i + 1) % len(points)]
            # Рисуем линию от текущей точки к следующей
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    @staticmethod
    def draw_angle(painter, vertex_x, vertex_y, point1_x, point1_y, point2_x, point2_y, radius=30):
        # Рисуем угол (две линии выходящие из одной точки)
        # vertex_x, vertex_y - вершина угла (точка где линии встречаются)
        # point1_x, point1_y - конец первой линии
        # point2_x, point2_y - конец второй линии
        # radius=30 - параметр по умолчанию (не используется тут)
        
        # Чёрное перо толщиной 2 пикселя
        painter.setPen(QPen(Qt.black, 2))
        # Рисуем первую линию от вершины к первой точке
        painter.drawLine(int(vertex_x), int(vertex_y), int(point1_x), int(point1_y))
        # Рисуем вторую линию от вершины ко второй точке
        painter.drawLine(int(vertex_x), int(vertex_y), int(point2_x), int(point2_y))